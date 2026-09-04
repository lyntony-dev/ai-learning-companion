"""feat-022 北极星指标聚合 (Tier 3-7) 测试。

覆盖:
  - north_star_metrics:活跃/问答轮次/拒答率/掌握进度/练习均分/结课漏斗
  - 空库全 0(无埋点不臆造)
  - 结课口径:仅当学员全部里程碑 passed 才计入 completed
  - HTTP:GET /insights/courses/{id}/metrics require_teacher(401/403/200)

用真实 tmp 业务库,离线可跑。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.course_pack import CoursePackLoader
from app.engine.insights import SqlInsightsService
from app.persistence import (
    CapstoneProject,
    ExerciseAttempt,
    Learner,
    Mastery,
    MasteryLevel,
    MilestoneProgress,
    MilestoneStatus,
    QaHistory,
    get_session,
    init_business_db,
    reset_engine,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_AGENT_EXISTS = (REPO_ROOT / "data" / "course_packs" / "ai_agent" / "manifest.yaml").exists()

pytestmark = pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")

ALL_MILESTONES = [
    "topic_selection",
    "architecture_design",
    "core_loop",
    "tool_integration",
    "evaluation",
    "delivery",
]


@pytest.fixture()
def business_db(tmp_path, monkeypatch):
    db = tmp_path / "business.sqlite"
    monkeypatch.setenv("BUSINESS_DB_URL", f"sqlite:///{db}")
    reset_engine()
    from app.core.config import Settings

    settings = Settings(_env_file=None, BUSINESS_DB_URL=f"sqlite:///{db}")
    init_business_db(settings)
    yield settings
    reset_engine()


def _service(settings):
    pack = CoursePackLoader().load("ai_agent")
    return SqlInsightsService(pack, settings=settings)


def _seed(settings) -> None:
    with get_session(settings) as s:
        for i in range(3):
            s.add(Learner(learner_id=f"stu_{i}"))
        # 掌握度:2 known + 1 unknown(taxonomy 内);1 条 taxonomy 外应被忽略
        s.add(Mastery(learner_id="stu_0", topic_id="langgraph.state", level=MasteryLevel.KNOWN))
        s.add(Mastery(learner_id="stu_1", topic_id="langchain.tools", level=MasteryLevel.KNOWN))
        s.add(Mastery(learner_id="stu_2", topic_id="langgraph.state", level=MasteryLevel.UNKNOWN))
        s.add(Mastery(learner_id="stu_0", topic_id="not.a.topic", level=MasteryLevel.KNOWN))
        # 问答:4 轮,其中 1 轮拒答
        for i in range(3):
            s.add(QaHistory(learner_id="stu_0", course_pack_id="ai_agent", refused=False))
        s.add(QaHistory(learner_id="stu_1", course_pack_id="ai_agent", refused=True))
        # 别的课程包的问答不应计入本课程
        s.add(QaHistory(learner_id="stu_1", course_pack_id="other", refused=True))
        # 练习:2 次 0.6/0.8
        s.add(ExerciseAttempt(learner_id="stu_0", question_id="q1", topic_id="langgraph.state", score=0.6))
        s.add(ExerciseAttempt(learner_id="stu_1", question_id="q1", topic_id="langgraph.state", score=0.8))
        # 立项:2 个
        s.add(CapstoneProject(learner_id="stu_0", course_pack_id="ai_agent", goal="做个客服 Agent"))
        s.add(CapstoneProject(learner_id="stu_1", course_pack_id="ai_agent", goal="做个检索 Agent"))
        # u0 全部里程碑 passed = 结课;u1 只过 1 个 = 未结课
        for m in ALL_MILESTONES:
            s.add(MilestoneProgress(learner_id="stu_0", course_pack_id="ai_agent", milestone=m, status=MilestoneStatus.PASSED))
        s.add(MilestoneProgress(learner_id="stu_1", course_pack_id="ai_agent", milestone="topic_selection", status=MilestoneStatus.PASSED))
        s.commit()


def test_metrics_empty_all_zero(business_db) -> None:
    out = _service(business_db).north_star_metrics("ai_agent")
    assert out["engagement"] == {"active_learners": 0, "qa_turns": 0, "practice_attempts": 0}
    assert out["honesty"]["refusal_rate"] == 0.0
    assert out["mastery_progress"]["known_rate"] == 0.0
    assert out["practice_quality"]["avg_score"] is None
    assert out["capstone_funnel"]["completion_rate"] == 0.0


def test_metrics_engagement_and_honesty(business_db) -> None:
    _seed(business_db)
    out = _service(business_db).north_star_metrics("ai_agent")
    assert out["engagement"]["active_learners"] == 3
    assert out["engagement"]["qa_turns"] == 4  # 只统计本课程包(排除 other)
    assert out["engagement"]["practice_attempts"] == 2
    assert out["honesty"]["refused"] == 1
    assert out["honesty"]["refusal_rate"] == pytest.approx(0.25, abs=1e-6)


def test_metrics_mastery_ignores_out_of_taxonomy(business_db) -> None:
    _seed(business_db)
    out = _service(business_db).north_star_metrics("ai_agent")
    # not.a.topic 被忽略:tracked=3, known=2
    assert out["mastery_progress"]["topics_tracked"] == 3
    assert out["mastery_progress"]["known"] == 2
    assert out["mastery_progress"]["known_rate"] == pytest.approx(2 / 3, abs=1e-4)


def test_metrics_practice_and_capstone_funnel(business_db) -> None:
    _seed(business_db)
    out = _service(business_db).north_star_metrics("ai_agent")
    assert out["practice_quality"]["avg_score"] == pytest.approx(0.7, abs=1e-6)
    assert out["capstone_funnel"]["kickoff"] == 2
    assert out["capstone_funnel"]["completed"] == 1  # 仅 u0 全里程碑通过
    assert out["capstone_funnel"]["completion_rate"] == pytest.approx(0.5, abs=1e-6)


# --- HTTP ---


@pytest.fixture()
def client(business_db):
    from app.core.config import get_settings
    from app.main import app

    app.dependency_overrides[get_settings] = lambda: business_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _teacher_headers(business_db) -> dict:
    from app.auth.security import sign_token

    token = sign_token("tea_prof", "prof", business_db.auth_token_secret, 168, role="teacher")
    return {"Authorization": f"Bearer {token}"}


def test_http_metrics_requires_teacher(client, business_db) -> None:
    assert client.get("/api/insights/courses/ai_agent/metrics").status_code == 401
    from app.auth.security import sign_token

    stu = sign_token("stu_a", "a", business_db.auth_token_secret, 168, role="student")
    r = client.get(
        "/api/insights/courses/ai_agent/metrics",
        headers={"Authorization": f"Bearer {stu}"},
    )
    assert r.status_code == 403


def test_http_metrics_ok(client, business_db) -> None:
    _seed(business_db)
    r = client.get(
        "/api/insights/courses/ai_agent/metrics", headers=_teacher_headers(business_db)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["course_pack_id"] == "ai_agent"
    assert body["engagement"]["qa_turns"] == 4
    assert body["honesty"]["refusal_rate"] == pytest.approx(0.25, abs=1e-6)
    assert body["capstone_funnel"]["completed"] == 1
