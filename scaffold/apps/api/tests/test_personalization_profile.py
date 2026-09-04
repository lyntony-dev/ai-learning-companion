"""画像驱动个性化测试(梯队二-4)。

覆盖:
  - SqlLearnerModel.learner_profile:读到自述画像 / 无记录返回空 dict
  - qa_graph._learner_profile_hint:空画像零影响;有画像拼出背景/目标/难度风格提示
  - _target_difficulty:偏好难度把掌握度目标难度往其方向拉半档;未设偏好则纯掌握度
  - 访客/未登录零回归:EmptyLearnerModel + 无 LearnerProfile 行为不变

用真实 tmp 业务库 + 注入 FakeLLM,离线可跑。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.course_pack import CoursePackLoader
from app.engine.learner_model import EmptyLearnerModel, SqlLearnerModel
from app.engine.orchestration.subgraphs.qa_graph import _learner_profile_hint
from app.engine.training import SqlTrainingService, seed_question_bank
from app.persistence import (
    Learner,
    LearnerProfile,
    Mastery,
    MasteryLevel,
    MasterySource,
    get_session,
    init_business_db,
    reset_engine,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_AGENT_EXISTS = (REPO_ROOT / "data" / "course_packs" / "ai_agent" / "manifest.yaml").exists()

pytestmark = pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")


class NeverCalledLLM:
    def complete(self, prompt, system=None, **kwargs):  # pragma: no cover
        raise AssertionError("不应触发 LLM 生成:应命中预置题库")


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


def _ensure_learner(settings, learner_id):
    with get_session(settings) as s:
        if s.get(Learner, learner_id) is None:
            s.add(Learner(learner_id=learner_id))
            s.commit()


def _set_profile(settings, learner_id, **fields):
    _ensure_learner(settings, learner_id)
    with get_session(settings) as s:
        s.add(LearnerProfile(learner_id=learner_id, **fields))
        s.commit()


def _set_mastery(settings, learner_id, topic_id, level):
    _ensure_learner(settings, learner_id)
    with get_session(settings) as s:
        s.add(
            Mastery(
                learner_id=learner_id,
                topic_id=topic_id,
                level=level,
                source=MasterySource.SYSTEM_INFERRED,
            )
        )
        s.commit()


# --- _learner_profile_hint(纯函数,零依赖) ---


def test_hint_empty_profile_returns_blank() -> None:
    assert _learner_profile_hint({}) == ""
    assert _learner_profile_hint({"background": "", "learning_goal": "", "preferred_difficulty": ""}) == ""


def test_hint_builds_background_goal_and_style() -> None:
    hint = _learner_profile_hint(
        {"background": "后端工程师", "learning_goal": "转 AI", "preferred_difficulty": "hard"}
    )
    assert "后端工程师" in hint
    assert "转 AI" in hint
    assert "挑战" in hint  # hard 风格提示


def test_hint_unknown_difficulty_ignored() -> None:
    hint = _learner_profile_hint({"preferred_difficulty": "expert"})
    assert hint == ""  # 非法难度值不产出风格提示


# --- SqlLearnerModel.learner_profile ---


def test_learner_profile_read(business_db) -> None:
    _set_profile(
        business_db,
        "u_prof",
        background="产品经理",
        learning_goal="理解 RAG",
        preferred_difficulty="easy",
    )
    lm = SqlLearnerModel(_pack(), settings=business_db)
    prof = lm.learner_profile("u_prof")
    assert prof == {
        "background": "产品经理",
        "learning_goal": "理解 RAG",
        "preferred_difficulty": "easy",
    }


def test_learner_profile_missing_returns_empty(business_db) -> None:
    lm = SqlLearnerModel(_pack(), settings=business_db)
    assert lm.learner_profile("nobody") == {}
    # 访客占位模型恒空
    assert EmptyLearnerModel().learner_profile("anyone") == {}


# --- _target_difficulty 偏好融合 ---


def test_target_difficulty_no_profile_uses_mastery(business_db) -> None:
    svc = SqlTrainingService(_pack(), llm=NeverCalledLLM(), settings=business_db)
    topic = "langchain.agent_basics"
    _set_mastery(business_db, "u_np", topic, MasteryLevel.UNKNOWN)  # → easy
    assert svc._target_difficulty("u_np", topic) == "easy"


def test_target_difficulty_preference_pulls_up(business_db) -> None:
    """掌握度 easy(0) + 偏好 hard(2) → 平均 1 → medium。"""
    svc = SqlTrainingService(_pack(), llm=NeverCalledLLM(), settings=business_db)
    topic = "langchain.agent_basics"
    _set_mastery(business_db, "u_up", topic, MasteryLevel.UNKNOWN)
    _set_profile(business_db, "u_up", preferred_difficulty="hard")
    assert svc._target_difficulty("u_up", topic) == "medium"


def test_target_difficulty_preference_pulls_down(business_db) -> None:
    """掌握度 hard(2) + 偏好 easy(0) → 平均 1 → medium。"""
    svc = SqlTrainingService(_pack(), llm=NeverCalledLLM(), settings=business_db)
    topic = "langchain.agent_basics"
    _set_mastery(business_db, "u_dn", topic, MasteryLevel.KNOWN)
    _set_profile(business_db, "u_dn", preferred_difficulty="easy")
    assert svc._target_difficulty("u_dn", topic) == "medium"


def test_target_difficulty_empty_preference_no_change(business_db) -> None:
    svc = SqlTrainingService(_pack(), llm=NeverCalledLLM(), settings=business_db)
    topic = "langchain.agent_basics"
    _set_mastery(business_db, "u_ep", topic, MasteryLevel.KNOWN)  # → hard
    _set_profile(business_db, "u_ep", preferred_difficulty="")  # 未设置
    assert svc._target_difficulty("u_ep", topic) == "hard"
