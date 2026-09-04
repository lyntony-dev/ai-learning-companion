"""feat-012 训练闭环 (E) HTTP 端点测试 (DESIGN §4)。

覆盖:
  - POST /questions:出题返回题目,且响应不含 reference_answer(防泄题)
  - POST /questions:无薄弱点时退到课程包首个知识点仍能出题
  - POST /grade:批改落 ExerciseAttempt + Mastery,返回分数/维度/mastery
  - POST /grade:question_id 不存在 → 404
  - 缺课程包 → 404

用真实 tmp 业务库 + mock LLM(默认 provider),离线可跑。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.persistence import (
    ExerciseAttempt,
    Mastery,
    QuestionBank,
    QuestionSource,
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


@pytest.fixture()
def client(business_db):
    from app.core.config import get_settings
    from app.main import app

    app.dependency_overrides[get_settings] = lambda: business_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _seed_question(settings, topic_id: str = "langgraph.state") -> str:
    """预置一道讲师已审核的题,使出题走题库(离线确定性)。"""
    qid = "q_seed_train"
    with get_session(settings) as s:
        s.add(
            QuestionBank(
                question_id=qid,
                course_pack_id="ai_agent",
                topic_id=topic_id,
                prompt="请解释 LangGraph 中 State 的作用。",
                reference_answer="State 在节点间传递上下文与中间结果。",
                source=QuestionSource.PRESET,
                approved_by="teacher_a",
            )
        )
        s.commit()
    return qid


def test_questions_returns_question_without_reference_answer(client, business_db) -> None:
    # 新学员无薄弱点 → 出题退到课程包首个知识点;把种子题放在首个知识点上,
    # 让出题走题库(离线确定性,不触发 LLM/检索)。
    _seed_question(business_db, topic_id="langchain.agent_basics")
    r = client.post("/api/training/courses/ai_agent/questions", json={"learner_id": "u1"})
    assert r.status_code == 200
    body = r.json()
    assert body["empty"] is False
    assert body["question_id"]
    assert body["prompt"]
    assert body["topic_name"]  # 补了知识点名
    # 防泄题:响应不含参考答案字段
    assert "reference_answer" not in body


def test_grade_persists_attempt_and_mastery(client, business_db) -> None:
    qid = _seed_question(business_db)
    r = client.post(
        "/api/training/courses/ai_agent/grade",
        json={"learner_id": "u1", "question_id": qid, "answer": "State 在节点间传递上下文与中间结果，保存对话历史。"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["question_id"] == qid
    assert 0.0 <= body["score"] <= 1.0
    assert isinstance(body["dimensions"], list) and body["dimensions"]
    assert body["mastery"]["topic_id"] == "langgraph.state"
    # 落库:ExerciseAttempt + Mastery
    with get_session(business_db) as s:
        attempts = s.exec(select(ExerciseAttempt).where(ExerciseAttempt.learner_id == "u1")).all()
        masteries = s.exec(select(Mastery).where(Mastery.learner_id == "u1")).all()
    assert len(attempts) == 1
    assert len(masteries) == 1


def test_grade_unknown_question_returns_404(client, business_db) -> None:
    r = client.post(
        "/api/training/courses/ai_agent/grade",
        json={"learner_id": "u1", "question_id": "nope", "answer": "x"},
    )
    assert r.status_code == 404
    assert "question_not_found" in r.json()["detail"]


def test_questions_course_not_found(client) -> None:
    r = client.post("/api/training/courses/no_such_pack/questions", json={"learner_id": "u1"})
    assert r.status_code == 404
    assert "course_pack_not_found" in r.json()["detail"]
