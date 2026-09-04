"""feat-006 纵切集成测试 A→B→C→D (DESIGN §4)。

用真实业务库(tmp SQLite via BUSINESS_DB_URL)+ 注入 FakeRetriever/FakeLLM,验证:
  A 问答:主图纵切产出带引用回答
  B Learner Model:问答后 mastery / qa_history 真实落库
  C 个性化:第二轮读到 weak_topics 并注入检索(retrieve weak_expanded=True)
  D 主动建议:opener/closing 真实生成
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.course_pack import CoursePackLoader
from app.engine.learner_model import SqlLearnerModel
from app.engine.orchestration.main_graph import build_main_graph, initial_state
from app.persistence import (
    Mastery,
    MasteryLevel,
    MasterySource,
    QaHistory,
    get_session,
    init_business_db,
    reset_engine,
)
from app.persistence.models import Learner
from sqlmodel import select

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_AGENT_EXISTS = (REPO_ROOT / "data" / "course_packs" / "ai_agent" / "manifest.yaml").exists()


class FakeRetriever:
    """返回带 langgraph_multiagent / langgraph.state 语义的强证据 chunk。"""

    def __init__(self) -> None:
        self.last_query = ""
        self.last_top_k = 0

    def retrieve(self, course_pack_id, query, course_ids=None, top_k=5):
        self.last_query = query
        self.last_top_k = top_k
        return [
            {
                "chunk_id": "c1",
                "text": "LangGraph 的 State 用于在节点之间共享上下文。",
                "score": 0.9,
                "metadata": {
                    "course_id": "langgraph_multiagent",
                    "section": "State",
                    "source_path": "s.html",
                    "slide_no": 3,
                },
            }
        ]


class FakeLLM:
    def complete(self, prompt, system=None, **kwargs):
        return "State 是跨节点共享的数据结构 [1]"


@pytest.fixture()
def business_db(tmp_path, monkeypatch):
    """把业务库指到 tmp,建表,测试后重置单例。"""
    db = tmp_path / "business.sqlite"
    monkeypatch.setenv("BUSINESS_DB_URL", f"sqlite:///{db}")
    reset_engine()
    from app.core.config import Settings

    settings = Settings(_env_file=None, BUSINESS_DB_URL=f"sqlite:///{db}")
    init_business_db(settings)
    yield settings
    reset_engine()


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_vertical_slice_a_b_c_d(business_db) -> None:
    settings = business_db
    pack = CoursePackLoader().load("ai_agent")
    learner = SqlLearnerModel(pack, settings=settings)
    retriever = FakeRetriever()

    graph = build_main_graph(retriever, llm=FakeLLM(), learner_model=learner)

    # --- 第一轮:A 问答 + B 落库 + D 建议 ---
    out1 = graph.invoke(
        initial_state("LangGraph 的 State 是什么?", "ai_agent", learner_id="stu1")
    )
    # A
    assert "[1]" in out1["answer"]
    assert out1["refused"] is False
    # D
    assert out1["session_opener"]
    assert out1["closing_suggestion"]
    nodes1 = [t["node"] for t in out1["trace"]]
    assert "learner_update" in nodes1

    # B:mastery / qa_history 落库
    with get_session(settings) as s:
        masteries = s.exec(select(Mastery).where(Mastery.learner_id == "stu1")).all()
        qa = s.exec(select(QaHistory).where(QaHistory.learner_id == "stu1")).all()
        assert s.get(Learner, "stu1") is not None
    assert len(qa) == 1
    # 命中 langgraph.state 知识点 → fuzzy(问答只到 fuzzy)
    touched = {m.topic_id: m for m in masteries}
    assert "langgraph.state" in touched
    assert touched["langgraph.state"].level == MasteryLevel.FUZZY
    assert touched["langgraph.state"].source == MasterySource.SYSTEM_INFERRED

    # --- 第二轮:C 读到 weak_topics 并注入检索 ---
    out2 = graph.invoke(
        initial_state("再讲讲状态图?", "ai_agent", learner_id="stu1")
    )
    assert out2["weak_topics"]  # 上一轮沉淀的 fuzzy 知识点
    assert "langgraph.state" in out2["weak_topics"]
    # C 检索扩展:retrieve 的 query 应并入薄弱点术语,top_k 放大
    retrieve_evt = next(t for t in out2["trace"] if t["node"] == "retrieve")
    assert retrieve_evt["metadata"].get("weak_expanded") is True
    assert retriever.last_top_k > 5


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_instructor_correction_not_overwritten_by_qa(business_db) -> None:
    """讲师修正为 known 后,问答接触不应下调/覆盖。"""
    settings = business_db
    pack = CoursePackLoader().load("ai_agent")
    learner = SqlLearnerModel(pack, settings=settings)

    with get_session(settings) as s:
        s.add(Learner(learner_id="stu2"))
        s.add(
            Mastery(
                learner_id="stu2",
                topic_id="langgraph.state",
                level=MasteryLevel.KNOWN,
                source=MasterySource.INSTRUCTOR_CORRECTED,
                updated_by="teacher_a",
            )
        )
        s.commit()

    graph = build_main_graph(FakeRetriever(), llm=FakeLLM(), learner_model=learner)
    graph.invoke(initial_state("LangGraph State?", "ai_agent", learner_id="stu2"))

    with get_session(settings) as s:
        m = s.exec(
            select(Mastery).where(
                Mastery.learner_id == "stu2", Mastery.topic_id == "langgraph.state"
            )
        ).one()
    assert m.level == MasteryLevel.KNOWN
    assert m.source == MasterySource.INSTRUCTOR_CORRECTED
    assert m.updated_by == "teacher_a"


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_refused_turn_does_not_infer_mastery(business_db) -> None:
    """拒答轮不应推断掌握度,但仍记 qa_history(refused=True)。"""
    settings = business_db
    pack = CoursePackLoader().load("ai_agent")
    learner = SqlLearnerModel(pack, settings=settings)

    class WeakRetriever:
        def retrieve(self, course_pack_id, query, course_ids=None, top_k=5):
            return [{"chunk_id": "x", "text": "无关", "score": 0.05, "metadata": {}}]

    graph = build_main_graph(WeakRetriever(), llm=FakeLLM(), learner_model=learner)
    out = graph.invoke(initial_state("查不到的问题", "ai_agent", learner_id="stu3", max_retry=1))
    assert out["refused"] is True

    with get_session(settings) as s:
        masteries = s.exec(select(Mastery).where(Mastery.learner_id == "stu3")).all()
        qa = s.exec(select(QaHistory).where(QaHistory.learner_id == "stu3")).all()
    assert masteries == []
    assert len(qa) == 1
    assert qa[0].refused is True
