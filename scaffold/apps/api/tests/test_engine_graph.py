"""feat-005 StateGraph 编排层测试 (ADR-0001/0004 / PRD GRAPH-001/002/003)。

覆盖硬验收:
  - GRAPH-001: 存在 State/Node/Edge/Conditional Edge/END
  - GRAPH-002: 真实 Query Rewrite 重试(证据不足触发 rewrite→retrieve 回环)
  - GRAPH-003: max_retry 退出(超限走 refuse,不编造)
外加:review 条件边(pass/revise/reject)、主图 Router 分派、C/D 装饰。

用注入的 FakeRetriever/FakeLLM,保持图逻辑与向量库/真实 LLM 解耦(离线可跑)。
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.engine.orchestration.main_graph import (
    build_main_graph,
    initial_state,
    route_by_task,
)
from app.engine.orchestration.subgraphs.qa_graph import (
    build_qa_graph,
    route_after_evidence,
    route_after_review,
)


class FakeRetriever:
    def __init__(self, chunks: list[dict], sequence: list[list[dict]] | None = None) -> None:
        self._chunks = chunks
        self._sequence = sequence
        self._calls = 0

    def retrieve(self, course_pack_id, query, course_ids=None, top_k=5):
        if self._sequence is not None:
            idx = min(self._calls, len(self._sequence) - 1)
            self._calls += 1
            return self._sequence[idx]
        self._calls += 1
        return self._chunks


class FakeLLM:
    def __init__(self, text: str = "答案正文 [1]") -> None:
        self._text = text

    def complete(self, prompt, system=None, **kwargs):
        return self._text


def _chunk(score: float, cid: str = "c1") -> dict:
    return {
        "chunk_id": cid,
        "text": "LangGraph State 跨节点共享上下文",
        "score": score,
        "metadata": {
            "course_id": "langgraph_multiagent",
            "section": "StateGraph",
            "source_path": "slides/s.html",
            "slide_no": 6,
            "anchor_type": "slide",
            "anchor_value": "6",
        },
    }


def _courseware_chunk(score: float = 0.9, cid: str = "cw1") -> dict:
    return {
        "chunk_id": cid,
        "text": "Agent 是模型加工具加决策循环",
        "score": score,
        "metadata": {
            "course_id": "langchain_agent",
            "section": "核心概念:Agent",
            "source_path": "langchain_agent.md",
            "anchor_type": "heading",
            "anchor_value": "concept-agent",
        },
    }


# --- GRAPH-001: 图结构存在性 ---


def test_graph001_structure_has_all_elements() -> None:
    g = build_qa_graph(FakeRetriever([_chunk(0.9)]), llm=FakeLLM(), compile_graph=False)
    assert isinstance(g, StateGraph)
    # 节点(Node)
    for n in ["retrieve", "evidence_check", "query_rewrite", "answer", "review", "final", "refuse"]:
        assert n in g.nodes
    # 编译成功即证明 Edge/Conditional Edge/END 连接合法
    compiled = g.compile()
    assert compiled is not None
    # 条件边路由函数覆盖三分支
    assert route_after_evidence({"evidence_sufficient": True}) == "answer"
    assert route_after_evidence(
        {"evidence_sufficient": False, "retry_count": 0, "max_retry": 1}
    ) == "query_rewrite"
    assert route_after_evidence(
        {"evidence_sufficient": False, "retry_count": 1, "max_retry": 1}
    ) == "refuse"


def test_review_conditional_edges() -> None:
    assert route_after_review({"review_verdict": "pass"}) == "final"
    assert route_after_review({"review_verdict": "revise"}) == "answer"
    assert route_after_review({"review_verdict": "reject"}) == "refuse"
    # 重生成次数耗尽:不再无限回环 answer,直接用现有答案收尾(不是证据不足,不拒答)
    assert (
        route_after_review(
            {"review_verdict": "revise", "generate_retry_count": 1, "max_generate_retry": 1}
        )
        == "final"
    )


def test_answer_review_loop_capped_when_never_cites() -> None:
    """真实 LLM 若回答从不带方括号引用,answer<->review 循环必须封顶退出,不能无限重生成。

    回归测试:route_after_review 曾对 revise 无条件回 answer,MockLLMClient 的输出恒带
    "[MOCK-LLM]" 前缀掩盖了这个问题;换成不带方括号的真实文本会暴露无限循环。
    """
    g = build_qa_graph(FakeRetriever([_chunk(0.9)]), llm=FakeLLM("纯文本回答,没有引用标记"))
    out = g.invoke(initial_state("State 是什么?", "ai_agent", max_generate_retry=1))
    nodes = [t["node"] for t in out["trace"]]
    assert nodes.count("answer") == 2  # 初次生成 + 1 次重生成,封顶后收尾
    assert nodes.count("review") == 2
    assert nodes[-1] == "final"
    assert out["refused"] is False
    assert out["generate_retry_count"] == 1


# --- 问答子图行为:证据足 → 正常回答 ---


def test_qa_strong_evidence_answers_with_citation() -> None:
    g = build_qa_graph(FakeRetriever([_chunk(0.9)]), llm=FakeLLM("这是回答 [1]"))
    state = initial_state("什么是 State?", "ai_agent")
    out = g.invoke(state)
    assert out["evidence_level"] == "strong"
    assert out["refused"] is False
    assert "[1]" in out["answer"]
    assert len(out["citations"]) == 1
    # 引用透传检索元数据的锚点(slide → 页码),供前端跳转
    assert out["citations"][0]["anchor_type"] == "slide"
    assert out["citations"][0]["anchor_value"] == "6"
    nodes = [t["node"] for t in out["trace"]]
    assert nodes == ["retrieve", "evidence_check", "answer", "review", "final"]


def test_qa_courseware_citation_carries_heading_anchor() -> None:
    """课件命中:引用携带 heading anchor,前端据此跳转课件对应标题。"""
    g = build_qa_graph(FakeRetriever([_courseware_chunk()]), llm=FakeLLM("这是回答 [1]"))
    out = g.invoke(initial_state("Agent 是什么?", "ai_agent"))
    assert len(out["citations"]) == 1
    c = out["citations"][0]
    assert c["anchor_type"] == "heading"
    assert c["anchor_value"] == "concept-agent"
    assert c["source_path"] == "langchain_agent.md"


# --- GRAPH-002: 真实 Rewrite 重试回环 ---


def test_graph002_rewrite_loop_then_recover() -> None:
    # 第一次检索弱证据,rewrite 后第二次强证据 → 成功回答
    seq = [[_chunk(0.1)], [_chunk(0.9)]]
    g = build_qa_graph(FakeRetriever([], sequence=seq), llm=FakeLLM("恢复回答 [1]"))
    out = g.invoke(initial_state("模糊问题", "ai_agent", max_retry=2))
    nodes = [t["node"] for t in out["trace"]]
    # 出现两次 retrieve + 一次 query_rewrite = 真实回环
    assert nodes.count("retrieve") == 2
    assert "query_rewrite" in nodes
    assert out["refused"] is False
    assert out["retry_count"] == 1
    # rewritten_query 与原 query 不同(真实改写)
    assert out["rewritten_query"] and out["rewritten_query"] != "模糊问题"


# --- GRAPH-003: max_retry 退出走拒答 ---


def test_graph003_max_retry_refuses() -> None:
    g = build_qa_graph(FakeRetriever([_chunk(0.1)]), llm=FakeLLM())
    out = g.invoke(initial_state("永远查不到", "ai_agent", max_retry=1))
    nodes = [t["node"] for t in out["trace"]]
    assert out["refused"] is True
    assert out["citations"] == []
    assert nodes[-1] == "refuse"
    # 恰好重试到上限:2 次 retrieve,1 次 rewrite,最后 refuse
    assert nodes.count("retrieve") == 2
    assert nodes.count("query_rewrite") == 1


# --- 主图 Router 分派 ---


def test_router_dispatch_targets() -> None:
    assert route_by_task({"task_type": "rag_answer"}) == "qa"
    assert route_by_task({"task_type": "direct_answer"}) == "qa"
    assert route_by_task({"task_type": "grade_homework"}) == "training"
    assert route_by_task({"task_type": "capstone"}) == "capstone"
    assert route_by_task({}) == "qa"


def test_main_graph_qa_slice_with_decorators() -> None:
    g = build_main_graph(FakeRetriever([_chunk(0.9)]), llm=FakeLLM("回答 [1]"))
    out = g.invoke(initial_state("State 是什么?", "ai_agent"))
    nodes = [t["node"] for t in out["trace"]]
    # C/D 装饰在两端 + 中间问答子图 + B 掌握度更新(trace 不重复)
    assert nodes[0] == "personalize_opener"
    assert nodes[1] == "router"
    assert nodes[-1] == "closing_advice"
    assert "learner_update" in nodes  # B:问答后掌握度更新
    assert nodes.count("personalize_opener") == 1  # 子图边界不重复
    assert out["session_opener"]
    assert out["closing_suggestion"]
    assert "[1]" in out["answer"]


def test_main_graph_training_stub_routes() -> None:
    g = build_main_graph(FakeRetriever([_chunk(0.9)]), llm=FakeLLM())
    out = g.invoke(initial_state("批改", "ai_agent", task_type="grade_homework"))
    nodes = [t["node"] for t in out["trace"]]
    assert "training" in nodes
    assert nodes[-1] == "closing_advice"


def test_main_graph_capstone_stub_routes() -> None:
    g = build_main_graph(FakeRetriever([_chunk(0.9)]), llm=FakeLLM())
    out = g.invoke(initial_state("项目", "ai_agent", task_type="capstone"))
    nodes = [t["node"] for t in out["trace"]]
    assert "capstone" in nodes


def test_personalization_injects_weak_topics() -> None:
    class WeakProvider:
        def profile(self, learner_id, course_pack_id):
            return {"langgraph.state": "fuzzy"}

        def weak_topics(self, learner_id, course_pack_id):
            return ["langgraph.state"]

        def record_qa_turn(self, state):
            return {"touched_topics": ["langgraph.state"], "mastery_updates": 0}

    g = build_main_graph(
        FakeRetriever([_chunk(0.9)]), llm=FakeLLM("回答 [1]"), learner_model=WeakProvider()
    )
    out = g.invoke(initial_state("问题", "ai_agent"))
    assert out["weak_topics"] == ["langgraph.state"]
    assert "langgraph.state" in out["session_opener"]
