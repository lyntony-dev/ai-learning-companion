"""训练闭环增强测试:预置题库入库 + 自适应/防重复选题 + 难度感知。

覆盖:
  - seed_question_bank 幂等且非破坏(不重复插入,不触碰 LLM 候选)
  - 自适应选题:掌握度弱→easy,已会→hard
  - 防重复选题:已做过的题会轮换到下一道
  - 预置题优先于 LLM 生成

用真实 tmp 业务库 + 注入 FakeLLM,离线可跑。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlmodel import select

from app.course_pack import CoursePackLoader
from app.engine.training import SqlTrainingService, preset_question_id, seed_question_bank
from app.persistence import (
    ExerciseAttempt,
    Learner,
    Mastery,
    MasteryLevel,
    MasterySource,
    QuestionBank,
    QuestionSource,
    get_session,
    init_business_db,
    reset_engine,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_AGENT_EXISTS = (REPO_ROOT / "data" / "course_packs" / "ai_agent" / "manifest.yaml").exists()

pytestmark = pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")


class NeverCalledLLM:
    """出题若走到 LLM 即测试失败(用于断言走的是预置题库)。"""

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


def _set_mastery(settings, learner_id, topic_id, level):
    with get_session(settings) as s:
        if s.get(Learner, learner_id) is None:
            s.add(Learner(learner_id=learner_id))
        s.add(
            Mastery(
                learner_id=learner_id,
                topic_id=topic_id,
                level=level,
                source=MasterySource.SYSTEM_INFERRED,
            )
        )
        s.commit()


def test_seed_is_idempotent_and_non_destructive(business_db) -> None:
    pack = _pack()
    n1 = seed_question_bank(pack, business_db)
    assert n1 > 0
    # 再次 seed 不应重复插入
    n2 = seed_question_bank(pack, business_db)
    assert n2 == 0

    with get_session(business_db) as s:
        preset_rows = s.exec(
            select(QuestionBank).where(QuestionBank.source == QuestionSource.PRESET)
        ).all()
    assert len(preset_rows) == n1
    # 预置题标记为课程包已沉淀
    assert all(r.approved_by == "course_pack" for r in preset_rows)
    assert all(r.difficulty in {"easy", "medium", "hard"} for r in preset_rows)


def test_seed_does_not_touch_llm_generated(business_db) -> None:
    pack = _pack()
    # 先放一条 LLM 候选
    with get_session(business_db) as s:
        s.add(
            QuestionBank(
                question_id="q_llm_candidate",
                course_pack_id="ai_agent",
                topic_id="langchain.agent_basics",
                prompt="候选题",
                reference_answer="",
                source=QuestionSource.LLM_GENERATED,
                approved_by="",
            )
        )
        s.commit()
    seed_question_bank(pack, business_db)
    with get_session(business_db) as s:
        row = s.get(QuestionBank, "q_llm_candidate")
    assert row is not None
    assert row.source == QuestionSource.LLM_GENERATED
    assert row.approved_by == ""  # 未被改动


def test_select_adaptive_difficulty_by_mastery(business_db) -> None:
    pack = _pack()
    seed_question_bank(pack, business_db)
    svc = SqlTrainingService(pack, llm=NeverCalledLLM(), settings=business_db)
    topic = "langchain.agent_basics"

    # 未知掌握度 → easy
    _set_mastery(business_db, "u_weak", topic, MasteryLevel.UNKNOWN)
    q_weak = svc.select_question("u_weak", "ai_agent", [topic])
    assert q_weak["difficulty"] == "easy"

    # 已掌握 → hard
    _set_mastery(business_db, "u_strong", topic, MasteryLevel.KNOWN)
    q_strong = svc.select_question("u_strong", "ai_agent", [topic])
    assert q_strong["difficulty"] == "hard"


def test_select_avoids_repeating_attempted_question(business_db) -> None:
    pack = _pack()
    seed_question_bank(pack, business_db)
    svc = SqlTrainingService(pack, llm=NeverCalledLLM(), settings=business_db)
    topic = "langchain.agent_basics"
    _set_mastery(business_db, "u1", topic, MasteryLevel.UNKNOWN)  # easy 档

    first = svc.select_question("u1", "ai_agent", [topic])
    # 记录一次作答
    svc.update_mastery("u1", first, {"score": 0.5, "feedback": ""})
    # easy 档只有一道题时会轮换回同题;此处 easy 档存在多道则应换题。
    second = svc.select_question("u1", "ai_agent", [topic])
    # 至少保证:若该难度存在未做过的题,不会再选到刚做过的那道
    with get_session(business_db) as s:
        easy_ids = [
            r.question_id
            for r in s.exec(
                select(QuestionBank).where(
                    QuestionBank.topic_id == topic, QuestionBank.difficulty == "easy"
                )
            ).all()
        ]
    if len(easy_ids) > 1:
        assert second["question_id"] != first["question_id"]


def test_preset_preferred_over_generation(business_db) -> None:
    pack = _pack()
    seed_question_bank(pack, business_db)
    # NeverCalledLLM 保证出题命中预置题库而非 LLM 生成
    svc = SqlTrainingService(pack, llm=NeverCalledLLM(), settings=business_db)
    q = svc.select_question("u1", "ai_agent", ["langchain.agent_basics"])
    assert q["source"] == QuestionSource.PRESET.value


def test_preset_question_id_slug_and_hash() -> None:
    with_slug = preset_question_id("ai_agent", "t.a", "prompt", "my_slug")
    assert with_slug == "q_preset_ai_agent_my_slug"
    hashed = preset_question_id("ai_agent", "t.a", "prompt")
    assert hashed.startswith("q_") and len(hashed) == 18


def test_next_question_excludes_seen_within_topic(business_db) -> None:
    """「换一题」回传已见题 id → 同知识点内返回不同题(修复恒定同题缺陷)。"""
    pack = _pack()
    seed_question_bank(pack, business_db)
    svc = SqlTrainingService(pack, llm=NeverCalledLLM(), settings=business_db)
    topic = "langchain.agent_basics"

    first = svc.select_question("u1", "ai_agent", [topic])
    # 未作答、仅「换一题」:靠 exclude_ids 跳过刚看过的题
    second = svc.select_question("u1", "ai_agent", [topic], exclude_ids=[first["question_id"]])
    assert second["question_id"] != first["question_id"]
    third = svc.select_question(
        "u1", "ai_agent", [topic],
        exclude_ids=[first["question_id"], second["question_id"]],
    )
    assert third["question_id"] not in {first["question_id"], second["question_id"]}


def test_next_question_rotates_to_next_topic_when_exhausted(business_db) -> None:
    """当前知识点的题都被排除 → 轮换到下一个知识点,而非卡在同题。"""
    pack = _pack()
    seed_question_bank(pack, business_db)
    svc = SqlTrainingService(pack, llm=NeverCalledLLM(), settings=business_db)
    topic = "langchain.agent_basics"

    with get_session(business_db) as s:
        topic_ids = [
            r.question_id
            for r in s.exec(
                select(QuestionBank).where(QuestionBank.topic_id == topic)
            ).all()
        ]
    # 排除该知识点全部预置题 → 应换到另一个知识点(NeverCalledLLM 保证不走生成)
    nxt = svc.select_question("u1", "ai_agent", [topic], exclude_ids=topic_ids)
    assert nxt["question_id"] not in set(topic_ids)
    assert nxt["topic_id"] != topic
    assert nxt["source"] == QuestionSource.PRESET.value

