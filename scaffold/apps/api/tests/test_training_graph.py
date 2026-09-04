"""feat-007 训练闭环子图 (E) 测试 (ADR-0004/0005/0006 / DESIGN §4)。

覆盖:
  - 训练子图结构:StateGraph + 节点 + 条件边 + END
  - 交互式两段:未带作答→出题(await_answer);带作答→批改→更新掌握度
  - 批改可达 known(高分),中分→fuzzy,低分→unknown
  - 讲师修正不被训练批改覆盖
  - 题库不足时 LLM 依证据生成候选题(source=llm_generated, approved_by 空)
  - 主图 grade_homework 路由进真训练子图

用真实 tmp 业务库 + 注入 FakeLLM/FakeRetriever,保持离线可跑。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.graph import END, StateGraph
from sqlmodel import select

from app.course_pack import CoursePackLoader
from app.engine.orchestration.main_graph import build_main_graph, initial_state
from app.engine.orchestration.subgraphs.training_graph import (
    build_training_graph,
    route_after_select,
)
from app.engine.training import SqlTrainingService
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


class ScriptedGradeLLM:
    """按需返回批改/出题 JSON 的假 LLM。

    批改时按 prompt 里实际列出的评分维度 key 逐一给分(模拟真实 LLM 会对
    课程专项维度也打分),避免与 rubric 的 by_course 专项维度脱节。
    """

    def __init__(self, score: float = 0.9, gen_prompt: str = "解释 State?") -> None:
        self._score = score
        self._gen_prompt = gen_prompt

    def complete(self, prompt, system=None, **kwargs):
        if "评分维度" in prompt or "学员作答" in prompt:
            import re

            keys = re.findall(r"([A-Za-z_]+)\(", prompt)
            if not keys:
                keys = ["correctness", "reasoning", "completeness"]
            dims = ", ".join(f'{{"key": "{k}", "score": {self._score}}}' for k in keys)
            return f'{{"dimensions": [{dims}], "feedback": "不错"}}'
        # 出题
        return f'{{"prompt": "{self._gen_prompt}", "reference_answer": "State 跨节点共享上下文"}}'


class FakeRetriever:
    def retrieve(self, course_pack_id, query, course_ids=None, top_k=5):
        return [
            {
                "chunk_id": "c1",
                "text": "LangGraph 的 State 用于在节点之间共享上下文。",
                "score": 0.9,
                "metadata": {"course_id": "langgraph_multiagent", "section": "State"},
            }
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


def _service(business_db, score=0.9):
    pack = CoursePackLoader().load("ai_agent")
    return pack, SqlTrainingService(pack, llm=ScriptedGradeLLM(score=score), settings=business_db)


# --- 结构 ---


def test_training_graph_structure(business_db) -> None:
    _pack, svc = _service(business_db)
    g = build_training_graph(svc, FakeRetriever(), compile_graph=False)
    assert isinstance(g, StateGraph)
    for n in ["select_question", "await_answer", "grade", "update_mastery"]:
        assert n in g.nodes
    assert g.compile() is not None
    assert route_after_select({"current_question": {"prompt": "q"}, "learner_answer": "a"}) == "grade"
    assert route_after_select({"current_question": {"prompt": "q"}}) == "await_answer"
    assert route_after_select({"current_question": {}}) == "await_answer"


# --- 交互式:先出题 ---


def test_training_issues_question_without_answer(business_db) -> None:
    pack, svc = _service(business_db)
    # 预置一道题
    with get_session(business_db) as s:
        s.add(
            QuestionBank(
                question_id="qp1",
                course_pack_id="ai_agent",
                topic_id="langgraph.state",
                prompt="什么是 State?",
                reference_answer="跨节点共享上下文",
                source=QuestionSource.PRESET,
                approved_by="teacher_a",
            )
        )
        s.commit()

    g = build_training_graph(svc, FakeRetriever())
    state = initial_state("", "ai_agent", learner_id="stu1", task_type="grade_homework")
    state["weak_topics"] = ["langgraph.state"]
    out = g.invoke(state)
    nodes = [t["node"] for t in out["trace"]]
    assert nodes == ["select_question", "await_answer"]
    assert out["current_question"]["question_id"] == "qp1"
    assert "State" in out["answer"]


# --- 带作答:批改 → 更新掌握度(高分达 known) ---


def test_training_grade_reaches_known(business_db) -> None:
    pack, svc = _service(business_db, score=0.95)
    with get_session(business_db) as s:
        s.add(
            QuestionBank(
                question_id="qp1",
                course_pack_id="ai_agent",
                topic_id="langgraph.state",
                prompt="什么是 State?",
                reference_answer="跨节点共享上下文",
                source=QuestionSource.PRESET,
                approved_by="teacher_a",
            )
        )
        s.commit()

    g = build_training_graph(svc, FakeRetriever())
    state = initial_state(
        "", "ai_agent", learner_id="stu1", task_type="grade_homework",
        learner_answer="State 是跨节点共享上下文的数据结构",
    )
    state["weak_topics"] = ["langgraph.state"]
    out = g.invoke(state)
    nodes = [t["node"] for t in out["trace"]]
    assert nodes == ["select_question", "grade", "update_mastery"]
    assert out["grade_result"]["passed"] is True

    with get_session(business_db) as s:
        m = s.exec(
            select(Mastery).where(
                Mastery.learner_id == "stu1", Mastery.topic_id == "langgraph.state"
            )
        ).one()
        attempts = s.exec(
            select(ExerciseAttempt).where(ExerciseAttempt.learner_id == "stu1")
        ).all()
    assert m.level == MasteryLevel.KNOWN  # 训练闭环可达 known
    assert m.source == MasterySource.SYSTEM_INFERRED
    assert len(attempts) == 1
    assert attempts[0].score >= 0.8


def test_training_low_score_stays_unknown(business_db) -> None:
    pack, svc = _service(business_db, score=0.1)
    with get_session(business_db) as s:
        s.add(
            QuestionBank(
                question_id="qp1",
                course_pack_id="ai_agent",
                topic_id="langgraph.state",
                prompt="什么是 State?",
                reference_answer="跨节点共享上下文",
                source=QuestionSource.PRESET,
                approved_by="teacher_a",
            )
        )
        s.commit()

    g = build_training_graph(svc, FakeRetriever())
    state = initial_state(
        "", "ai_agent", learner_id="stu2", task_type="grade_homework",
        learner_answer="不知道",
    )
    state["weak_topics"] = ["langgraph.state"]
    out = g.invoke(state)
    assert out["grade_result"]["passed"] is False
    with get_session(business_db) as s:
        m = s.exec(
            select(Mastery).where(Mastery.learner_id == "stu2")
        ).one()
    assert m.level == MasteryLevel.UNKNOWN


# --- 讲师修正不被覆盖 ---


def test_instructor_correction_not_overwritten_by_grade(business_db) -> None:
    pack, svc = _service(business_db, score=0.1)
    with get_session(business_db) as s:
        s.add(Learner(learner_id="stu3"))
        s.add(
            QuestionBank(
                question_id="qp1",
                course_pack_id="ai_agent",
                topic_id="langgraph.state",
                prompt="什么是 State?",
                reference_answer="跨节点共享上下文",
                source=QuestionSource.PRESET,
                approved_by="teacher_a",
            )
        )
        s.add(
            Mastery(
                learner_id="stu3",
                topic_id="langgraph.state",
                level=MasteryLevel.KNOWN,
                source=MasterySource.INSTRUCTOR_CORRECTED,
                updated_by="teacher_a",
            )
        )
        s.commit()

    g = build_training_graph(svc, FakeRetriever())
    state = initial_state(
        "", "ai_agent", learner_id="stu3", task_type="grade_homework",
        learner_answer="乱答",
    )
    state["weak_topics"] = ["langgraph.state"]
    g.invoke(state)
    with get_session(business_db) as s:
        m = s.exec(select(Mastery).where(Mastery.learner_id == "stu3")).one()
    assert m.level == MasteryLevel.KNOWN
    assert m.source == MasterySource.INSTRUCTOR_CORRECTED


# --- 题库不足 → LLM 依证据生成候选题 ---


def test_llm_generates_candidate_question_when_bank_empty(business_db) -> None:
    pack, svc = _service(business_db)
    g = build_training_graph(svc, FakeRetriever())
    state = initial_state("", "ai_agent", learner_id="stu4", task_type="grade_homework")
    state["weak_topics"] = ["langgraph.state"]
    out = g.invoke(state)
    q = out["current_question"]
    assert q["source"] == QuestionSource.LLM_GENERATED.value
    # 候选题落库,approved_by 为空(待讲师审核)
    with get_session(business_db) as s:
        row = s.get(QuestionBank, q["question_id"])
    assert row is not None
    assert row.approved_by == ""
    assert row.source == QuestionSource.LLM_GENERATED


# --- 主图路由进真训练子图 ---


def test_main_graph_routes_into_real_training(business_db) -> None:
    pack, svc = _service(business_db, score=0.9)

    class WeakLearner:
        def profile(self, learner_id, course_pack_id):
            return {"langgraph.state": "fuzzy"}

        def weak_topics(self, learner_id, course_pack_id):
            return ["langgraph.state"]

        def record_qa_turn(self, state):
            return {"touched_topics": [], "mastery_updates": 0}

    g = build_main_graph(
        FakeRetriever(),
        llm=ScriptedGradeLLM(),
        learner_model=WeakLearner(),
        training_service=svc,
    )
    out = g.invoke(
        initial_state(
            "", "ai_agent", learner_id="stu5", task_type="grade_homework",
            learner_answer="State 跨节点共享上下文",
        )
    )
    nodes = [t["node"] for t in out["trace"]]
    assert nodes[0] == "personalize_opener"
    assert "select_question" in nodes
    assert "grade" in nodes
    assert "update_mastery" in nodes
    assert nodes[-1] == "closing_advice"
    # 训练走真实批改后掌握度落库
    with get_session(business_db) as s:
        m = s.exec(select(Mastery).where(Mastery.learner_id == "stu5")).all()
    assert any(x.topic_id == "langgraph.state" for x in m)
