"""feat-009 教学洞察 per-course 聚合只读 (T) 测试 (ADR-0005 / DESIGN §4)。

覆盖:
  - course_insights:GROUP BY topic_id 掌握度分布 + 做题均分 + milestone 分布
  - weak_ranking:薄弱知识点(unknown+fuzzy)降序
  - learner_profile:单学员只读档案
  - correct_mastery:讲师修正标 INSTRUCTOR_CORRECTED + updated_by,幂等
  - correct_mastery 拒绝 taxonomy 外 topic / 缺 updated_by
  - HTTP:GET /insights/courses/{id}、learners/{id}、POST mastery-corrections、404

用真实 tmp 业务库,离线可跑。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.course_pack import CoursePackLoader
from app.engine.insights import SqlInsightsService
from app.persistence import (
    ExerciseAttempt,
    Learner,
    Mastery,
    MasteryLevel,
    MasterySource,
    MilestoneProgress,
    MilestoneStatus,
    get_session,
    init_business_db,
    reset_engine,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_AGENT_EXISTS = (REPO_ROOT / "data" / "course_packs" / "ai_agent" / "manifest.yaml").exists()

pytestmark = pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")


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


def _seed(settings) -> None:
    with get_session(settings) as s:
        for i in range(3):
            s.add(Learner(learner_id=f"stu_{i}"))
        # langgraph.state: 2 unknown + 1 known;langgraph.nodes_edges: 1 fuzzy
        s.add(Mastery(learner_id="stu_0", topic_id="langgraph.state", level=MasteryLevel.UNKNOWN))
        s.add(Mastery(learner_id="stu_1", topic_id="langgraph.state", level=MasteryLevel.UNKNOWN))
        s.add(Mastery(learner_id="stu_2", topic_id="langgraph.state", level=MasteryLevel.KNOWN))
        s.add(Mastery(learner_id="stu_0", topic_id="langgraph.nodes_edges", level=MasteryLevel.FUZZY))
        # 做题:langgraph.state 两次 0.6/0.8
        s.add(ExerciseAttempt(learner_id="stu_0", question_id="q1", topic_id="langgraph.state", score=0.6))
        s.add(ExerciseAttempt(learner_id="stu_1", question_id="q1", topic_id="langgraph.state", score=0.8))
        # 里程碑
        s.add(MilestoneProgress(learner_id="stu_0", course_pack_id="ai_agent", milestone="topic_selection", status=MilestoneStatus.PASSED))
        s.add(MilestoneProgress(learner_id="stu_1", course_pack_id="ai_agent", milestone="topic_selection", status=MilestoneStatus.IN_PROGRESS))
        s.commit()


def _service(settings):
    pack = CoursePackLoader().load("ai_agent")
    return SqlInsightsService(pack, settings=settings)


# --- 聚合 ---


def test_course_insights_aggregation(business_db) -> None:
    _seed(business_db)
    svc = _service(business_db)
    out = svc.course_insights("ai_agent")
    assert out["learner_count"] == 3
    topics = {t["topic_id"]: t for t in out["topics"]}
    st = topics["langgraph.state"]
    assert st["unknown"] == 2
    assert st["known"] == 1
    assert st["attempts"] == 2
    assert st["avg_score"] == pytest.approx(0.7, abs=1e-6)
    # 薄弱排行:langgraph.state(unknown2)排在 nodes_edges(fuzzy1)前
    ranking_ids = [t["topic_id"] for t in out["weak_ranking"]]
    assert ranking_ids.index("langgraph.state") < ranking_ids.index("langgraph.nodes_edges")
    # 里程碑分布
    ms = {m["milestone"]: m for m in out["milestones"]}
    assert ms["topic_selection"]["passed"] == 1
    assert ms["topic_selection"]["in_progress"] == 1


def test_learner_count_excludes_teachers(business_db) -> None:
    # 注册讲师也会写一行 Learner(tea_ 前缀),但不应计入学员数量统计
    _seed(business_db)  # stu_0/1/2
    with get_session(business_db) as s:
        s.add(Learner(learner_id="tea_prof"))
        s.commit()
    svc = _service(business_db)
    assert svc.course_insights("ai_agent")["learner_count"] == 3
    assert svc.north_star_metrics("ai_agent")["engagement"]["active_learners"] == 3


def test_learner_profile_readonly(business_db) -> None:
    _seed(business_db)
    svc = _service(business_db)
    prof = svc.learner_profile("stu_0", "ai_agent")
    tids = {m["topic_id"] for m in prof["masteries"]}
    assert "langgraph.state" in tids
    assert "langgraph.nodes_edges" in tids


def test_learner_profile_unknown_learner_raises(business_db) -> None:
    _seed(business_db)
    svc = _service(business_db)
    from app.engine.insights import LearnerNotFoundError

    with pytest.raises(LearnerNotFoundError):
        svc.learner_profile("ghost", "ai_agent")


def test_list_learners_aggregates_mastery(business_db) -> None:
    with get_session(business_db) as s:
        s.add(Learner(learner_id="stu_a"))
        s.add(Learner(learner_id="stu_b"))
        s.add(Learner(learner_id="tea_prof"))  # 讲师不应出现在学员列表
        s.add(Mastery(learner_id="stu_a", topic_id="langgraph.state", level=MasteryLevel.UNKNOWN))
        s.add(Mastery(learner_id="stu_a", topic_id="langgraph.nodes_edges", level=MasteryLevel.FUZZY))
        s.add(Mastery(learner_id="stu_b", topic_id="langgraph.state", level=MasteryLevel.KNOWN))
        s.commit()
    svc = _service(business_db)
    out = svc.list_learners("ai_agent")
    ids = {it["learner_id"] for it in out["items"]}
    assert ids == {"stu_a", "stu_b"}  # 讲师 tea_prof 被排除
    assert out["total"] == 2
    by_id = {it["learner_id"]: it for it in out["items"]}
    assert by_id["stu_a"]["unknown"] == 1
    assert by_id["stu_a"]["fuzzy"] == 1
    assert by_id["stu_a"]["tracked_topics"] == 2
    # stu_b: known 最多,排最前
    assert by_id["stu_b"]["known"] == 1
    assert out["items"][0]["learner_id"] == "stu_b"


def test_list_learners_pagination(business_db) -> None:
    with get_session(business_db) as s:
        for i in range(3):
            s.add(Learner(learner_id=f"stu_{i}"))
        s.commit()
    svc = _service(business_db)
    page = svc.list_learners("ai_agent", limit=2, offset=0)
    assert page["total"] == 3
    assert len(page["items"]) == 2
    assert page["limit"] == 2
    rest = svc.list_learners("ai_agent", limit=2, offset=2)
    assert len(rest["items"]) == 1


# --- 讲师修正 ---


def test_correct_mastery_marks_instructor_source(business_db) -> None:
    _seed(business_db)
    svc = _service(business_db)
    res = svc.correct_mastery("stu_0", "langgraph.state", MasteryLevel.KNOWN, "teacher_a")
    assert res["source"] == MasterySource.INSTRUCTOR_CORRECTED.value
    with get_session(business_db) as s:
        from sqlmodel import select

        m = s.exec(
            select(Mastery).where(
                Mastery.learner_id == "stu_0", Mastery.topic_id == "langgraph.state"
            )
        ).one()
    assert m.level == MasteryLevel.KNOWN
    assert m.source == MasterySource.INSTRUCTOR_CORRECTED
    assert m.updated_by == "teacher_a"


def test_correct_mastery_rejects_invalid_topic(business_db) -> None:
    svc = _service(business_db)
    with pytest.raises(ValueError):
        svc.correct_mastery("stu_0", "not.a.topic", MasteryLevel.KNOWN, "teacher_a")
    with pytest.raises(ValueError):
        svc.correct_mastery("stu_0", "langgraph.state", MasteryLevel.KNOWN, "")


def test_correct_mastery_is_idempotent(business_db) -> None:
    svc = _service(business_db)
    svc.correct_mastery("u9", "langgraph.state", MasteryLevel.FUZZY, "t1")
    svc.correct_mastery("u9", "langgraph.state", MasteryLevel.KNOWN, "t2")
    with get_session(business_db) as s:
        from sqlmodel import select

        rows = s.exec(
            select(Mastery).where(Mastery.learner_id == "u9")
        ).all()
    assert len(rows) == 1  # upsert 不重复建行
    assert rows[0].level == MasteryLevel.KNOWN
    assert rows[0].updated_by == "t2"


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
    """签发一个讲师 token 供受保护的 insights 端点使用。"""
    from app.auth.security import sign_token

    token = sign_token(
        "tea_prof", "prof", business_db.auth_token_secret, 168, role="teacher"
    )
    return {"Authorization": f"Bearer {token}"}


def test_http_requires_teacher(client, business_db) -> None:
    # 无 token → 401
    assert client.get("/api/insights/courses/ai_agent").status_code == 401
    # 学生 token → 403
    from app.auth.security import sign_token

    stu = sign_token("stu_a", "a", business_db.auth_token_secret, 168, role="student")
    r = client.get(
        "/api/insights/courses/ai_agent",
        headers={"Authorization": f"Bearer {stu}"},
    )
    assert r.status_code == 403


def test_http_course_insights(client, business_db) -> None:
    _seed(business_db)
    r = client.get("/api/insights/courses/ai_agent", headers=_teacher_headers(business_db))
    assert r.status_code == 200
    body = r.json()
    assert body["learner_count"] == 3
    assert any(t["topic_id"] == "langgraph.state" for t in body["topics"])


def test_http_learner_profile(client, business_db) -> None:
    _seed(business_db)
    r = client.get(
        "/api/insights/courses/ai_agent/learners/stu_0", headers=_teacher_headers(business_db)
    )
    assert r.status_code == 200
    assert r.json()["learner_id"] == "stu_0"


def test_http_learner_profile_not_found(client, business_db) -> None:
    _seed(business_db)
    r = client.get(
        "/api/insights/courses/ai_agent/learners/ghost",
        headers=_teacher_headers(business_db),
    )
    assert r.status_code == 404


def test_http_list_learners(client, business_db) -> None:
    # 只列学员(stu_ 前缀),讲师(tea_ 前缀)不应出现
    with get_session(business_db) as s:
        s.add(Learner(learner_id="stu_0"))
        s.add(Learner(learner_id="stu_1"))
        s.add(Learner(learner_id="stu_2"))
        s.add(Learner(learner_id="tea_prof"))
        s.commit()
    r = client.get(
        "/api/insights/courses/ai_agent/learners", headers=_teacher_headers(business_db)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert {it["learner_id"] for it in body["items"]} == {"stu_0", "stu_1", "stu_2"}
    # 无 token → 401(require_teacher)
    assert client.get("/api/insights/courses/ai_agent/learners").status_code == 401


def test_http_mastery_correction(client, business_db) -> None:
    headers = _teacher_headers(business_db)
    r = client.post(
        "/api/insights/courses/ai_agent/mastery-corrections",
        json={
            "learner_id": "stu_0",
            "topic_id": "langgraph.state",
            "level": "known",
        },
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "instructor_corrected"
    assert body["updated_by"] == "prof"  # 以认证讲师身份为准,非请求体

    # taxonomy 外 topic → 422
    bad = client.post(
        "/api/insights/courses/ai_agent/mastery-corrections",
        json={
            "learner_id": "stu_0",
            "topic_id": "nope",
            "level": "known",
        },
        headers=headers,
    )
    assert bad.status_code == 422


def test_http_course_not_found(client, business_db) -> None:
    r = client.get(
        "/api/insights/courses/no_such_pack", headers=_teacher_headers(business_db)
    )
    assert r.status_code == 404
