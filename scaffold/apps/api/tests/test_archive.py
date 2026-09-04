"""我的学习档案聚合测试(梯队二-6)。

覆盖:
  - learning_archive:掌握度分布 + 练习记录(次数/均分/最近5) + 项目进度聚合
  - 只认本人 learner_id 数据(他人数据不串)
  - 只保留本课程包 taxonomy 内知识点
  - HTTP:GET /api/archive/courses/{id} 强制登录(无 token 401);
    token 身份权威(只读自己),课程包不存在 404

用真实 tmp 业务库,离线可跑。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.course_pack import CoursePackLoader
from app.engine.learner_model import SqlLearnerModel
from app.persistence import (
    CapstoneProject,
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

TOPIC = "langchain.agent_basics"


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


def _pack():
    return CoursePackLoader().load("ai_agent")


def _ensure(session, learner_id):
    if session.get(Learner, learner_id) is None:
        session.add(Learner(learner_id=learner_id))


def _seed_learner(business_db, learner_id):
    with get_session(business_db) as s:
        _ensure(s, learner_id)
        s.add(
            Mastery(
                learner_id=learner_id,
                topic_id=TOPIC,
                level=MasteryLevel.KNOWN,
                source=MasterySource.INSTRUCTOR_CORRECTED,
            )
        )
        s.add(
            Mastery(
                learner_id=learner_id,
                topic_id="not.a.topic",  # taxonomy 外,应被过滤
                level=MasteryLevel.FUZZY,
                source=MasterySource.SYSTEM_INFERRED,
            )
        )
        s.add(ExerciseAttempt(learner_id=learner_id, question_id="q1", topic_id=TOPIC, score=0.9))
        s.add(ExerciseAttempt(learner_id=learner_id, question_id="q2", topic_id=TOPIC, score=0.5))
        s.commit()


def test_archive_aggregates_self_data(business_db) -> None:
    _seed_learner(business_db, "stu_alice")
    model = SqlLearnerModel(_pack(), settings=business_db)
    arc = model.learning_archive("stu_alice", "ai_agent")

    # taxonomy 外知识点被过滤 → 只留 1 个已知
    assert arc["topics_tracked"] == 1
    assert arc["levels"]["known"] == 1
    assert all(m["topic_id"] == TOPIC for m in arc["masteries"])
    # 练习:2 次,均分 (0.9+0.5)/2=0.7
    assert arc["practice"]["attempts"] == 2
    assert arc["practice"]["avg_score"] == 0.7
    assert len(arc["practice"]["recent"]) == 2
    # 项目:未立项
    assert arc["capstone"]["has_project"] is False
    assert arc["capstone"]["total"] == len(_pack().milestone_ids())


def test_archive_isolates_other_learners(business_db) -> None:
    _seed_learner(business_db, "stu_alice")
    _seed_learner(business_db, "stu_bob")
    model = SqlLearnerModel(_pack(), settings=business_db)
    arc = model.learning_archive("stu_alice", "ai_agent")
    # alice 只看到自己的 2 次练习,不含 bob
    assert arc["practice"]["attempts"] == 2


def test_archive_includes_capstone_progress(business_db) -> None:
    milestone_ids = _pack().milestone_ids()
    assert milestone_ids  # 课程包应有里程碑
    first = milestone_ids[0]
    with get_session(business_db) as s:
        _ensure(s, "stu_c")
        s.add(
            CapstoneProject(
                learner_id="stu_c",
                course_pack_id="ai_agent",
                goal="做一个客服 Agent",
            )
        )
        s.add(
            MilestoneProgress(
                learner_id="stu_c",
                course_pack_id="ai_agent",
                milestone=first,
                status=MilestoneStatus.PASSED,
            )
        )
        s.commit()
    model = SqlLearnerModel(_pack(), settings=business_db)
    arc = model.learning_archive("stu_c", "ai_agent")
    assert arc["capstone"]["has_project"] is True
    assert arc["capstone"]["goal"] == "做一个客服 Agent"
    assert arc["capstone"]["passed"] == 1


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


def _student_headers(business_db, learner_id="stu_alice", username="alice") -> dict:
    from app.auth.security import sign_token

    token = sign_token(learner_id, username, business_db.auth_token_secret, 168, role="student")
    return {"Authorization": f"Bearer {token}"}


def test_http_archive_requires_login(client) -> None:
    assert client.get("/api/archive/courses/ai_agent").status_code == 401


def test_http_archive_returns_self(client, business_db) -> None:
    _seed_learner(business_db, "stu_alice")
    r = client.get(
        "/api/archive/courses/ai_agent", headers=_student_headers(business_db)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["learner_id"] == "stu_alice"
    assert body["practice"]["attempts"] == 2


def test_http_archive_course_not_found(client, business_db) -> None:
    r = client.get(
        "/api/archive/courses/no_such_pack", headers=_student_headers(business_db)
    )
    assert r.status_code == 404
