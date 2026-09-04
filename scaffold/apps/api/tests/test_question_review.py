"""讲师审核沉淀流测试(梯队二-5,ADR-0006 飞轮)。

覆盖:
  - list_candidate_questions:只列 LLM 生成且未审核(approved_by 空)的候选,含参考答案
  - approve_question:写 approved_by(讲师身份派生),幂等;跨包/不存在 ValueError
  - reject_question:删待审候选;已沉淀/预置题不可驳回;不存在 ValueError
  - 审核通过后 select_question 优先命中该题(飞轮闭环)
  - HTTP:候选列表/通过/驳回均 require_teacher(无 token 401、学生 403);
    通过响应 approved_by 以认证讲师为准

用真实 tmp 业务库 + 注入 FakeLLM,离线可跑。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.course_pack import CoursePackLoader
from app.engine.training import SqlTrainingService, seed_question_bank
from app.persistence import (
    QuestionBank,
    QuestionSource,
    get_session,
    init_business_db,
    reset_engine,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_AGENT_EXISTS = (REPO_ROOT / "data" / "course_packs" / "ai_agent" / "manifest.yaml").exists()

pytestmark = pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")

TOPIC = "langchain.agent_basics"


class NeverCalledLLM:
    def complete(self, prompt, system=None, **kwargs):  # pragma: no cover
        raise AssertionError("不应触发 LLM 生成")


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


def _svc(business_db):
    return SqlTrainingService(_pack(), llm=NeverCalledLLM(), settings=business_db)


def _add_candidate(business_db, qid, approved_by="", source=QuestionSource.LLM_GENERATED):
    with get_session(business_db) as s:
        s.add(
            QuestionBank(
                question_id=qid,
                course_pack_id="ai_agent",
                topic_id=TOPIC,
                prompt=f"候选题 {qid}",
                reference_answer="参考要点",
                difficulty="medium",
                source=source,
                approved_by=approved_by,
            )
        )
        s.commit()


# --- 服务层 ---


def test_list_only_unapproved_llm_candidates(business_db) -> None:
    seed_question_bank(_pack(), business_db)  # 预置题(approved_by=course_pack)不应入列
    _add_candidate(business_db, "q_cand_1")
    _add_candidate(business_db, "q_cand_2")
    _add_candidate(business_db, "q_approved", approved_by="prof")  # 已审核不入列
    svc = _svc(business_db)
    cands = svc.list_candidate_questions("ai_agent")
    ids = {c["question_id"] for c in cands}
    assert ids == {"q_cand_1", "q_cand_2"}
    # 候选含参考答案与知识点名(供讲师判断)
    assert all(c["reference_answer"] for c in cands)
    assert all(c["topic_name"] for c in cands)


def test_approve_sets_approved_by_and_is_idempotent(business_db) -> None:
    _add_candidate(business_db, "q_cand_1")
    svc = _svc(business_db)
    r1 = svc.approve_question("ai_agent", "q_cand_1", approved_by="prof")
    assert r1["approved_by"] == "prof"
    # 已审核不再出现在候选列表
    assert svc.list_candidate_questions("ai_agent") == []
    # 幂等:再次审核只覆盖 approved_by
    r2 = svc.approve_question("ai_agent", "q_cand_1", approved_by="prof2")
    assert r2["approved_by"] == "prof2"


def test_approve_requires_approved_by_and_valid_target(business_db) -> None:
    _add_candidate(business_db, "q_cand_1")
    svc = _svc(business_db)
    with pytest.raises(ValueError):
        svc.approve_question("ai_agent", "q_cand_1", approved_by="")
    with pytest.raises(ValueError):
        svc.approve_question("ai_agent", "nope", approved_by="prof")
    with pytest.raises(ValueError):
        svc.approve_question("other_pack", "q_cand_1", approved_by="prof")


def test_reject_deletes_candidate_only(business_db) -> None:
    _add_candidate(business_db, "q_cand_1")
    _add_candidate(business_db, "q_approved", approved_by="prof")
    svc = _svc(business_db)
    r = svc.reject_question("ai_agent", "q_cand_1")
    assert r["rejected"] is True
    with get_session(business_db) as s:
        assert s.get(QuestionBank, "q_cand_1") is None
    # 已沉淀题不可驳回
    with pytest.raises(ValueError):
        svc.reject_question("ai_agent", "q_approved")


def test_approved_candidate_preferred_in_selection(business_db) -> None:
    """飞轮闭环:审核通过后该候选题成为优先出题来源。"""
    _add_candidate(business_db, "q_cand_1")
    svc = _svc(business_db)
    svc.approve_question("ai_agent", "q_cand_1", approved_by="prof")
    q = svc.select_question("u1", "ai_agent", [TOPIC])
    assert q["question_id"] == "q_cand_1"


# --- HTTP(require_teacher 守卫) ---


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


def test_http_candidates_require_teacher(client, business_db) -> None:
    from app.auth.security import sign_token

    # 无 token → 401
    assert client.get("/api/training/courses/ai_agent/candidates").status_code == 401
    # 学生 token → 403
    stu = sign_token("stu_a", "a", business_db.auth_token_secret, 168, role="student")
    r = client.get(
        "/api/training/courses/ai_agent/candidates",
        headers={"Authorization": f"Bearer {stu}"},
    )
    assert r.status_code == 403


def test_http_list_and_approve_and_reject(client, business_db) -> None:
    _add_candidate(business_db, "q_cand_1")
    _add_candidate(business_db, "q_cand_2")
    headers = _teacher_headers(business_db)

    listed = client.get("/api/training/courses/ai_agent/candidates", headers=headers)
    assert listed.status_code == 200
    assert {c["question_id"] for c in listed.json()["candidates"]} == {"q_cand_1", "q_cand_2"}

    # 通过:approved_by 以认证讲师(username=prof)为准
    ap = client.post(
        "/api/training/courses/ai_agent/candidates/q_cand_1/approve", headers=headers
    )
    assert ap.status_code == 200
    assert ap.json()["approved_by"] == "prof"

    # 驳回另一条
    rj = client.post(
        "/api/training/courses/ai_agent/candidates/q_cand_2/reject", headers=headers
    )
    assert rj.status_code == 200 and rj.json()["rejected"] is True

    # 候选清空(一通过一驳回)
    remaining = client.get("/api/training/courses/ai_agent/candidates", headers=headers)
    assert remaining.json()["candidates"] == []


def test_http_approve_missing_returns_404(client, business_db) -> None:
    r = client.post(
        "/api/training/courses/ai_agent/candidates/nope/approve",
        headers=_teacher_headers(business_db),
    )
    assert r.status_code == 404
