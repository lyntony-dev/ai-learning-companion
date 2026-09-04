"""问答子图 (ADR-0001/0004 / DESIGN §4.3)。

承载 PRD 硬验收 GRAPH-001/002/003:
  - 真实 StateGraph:State + Node + Edge + Conditional Edge + END
  - 证据不足 → query_rewrite → retrieve 真实回环
  - retry_count >= max_retry → refuse 退出(不编造页码)
  - review 条件边:pass→final / revise→answer(封顶 max_generate_retry,耗尽→final)/ reject→refuse

节点:
  retrieve → evidence_check ─┬─(足)→ answer → review ─┬─(pass)→ final → END
                             ├─(不足,未超限)→ query_rewrite ↺ retrieve
                             └─(不足,超限)→ refuse → END
                                                review ─(revise,未超限)→ answer
                                                review ─(revise,超限)→ final
                                                review ─(reject)→ refuse

C 画像装饰(personalization)在 retrieve/answer 前后注入,见 decorators/。
真实 LLM 生成走 get_llm_client();检索走注入的 Retriever。
"""

from __future__ import annotations

from typing import Callable

from langgraph.graph import END, StateGraph

from app.engine.orchestration.state import TutorState, append_trace, new_trace_event
from app.engine.retrieval import Retriever
from app.llm import LLMClient, get_llm_client

STRONG_EVIDENCE_THRESHOLD = 0.75
WEAK_EVIDENCE_THRESHOLD = 0.35

_ANSWER_SYSTEM = (
    "你是课程学习助手。只依据提供的课程材料片段回答,"
    "在句末用 [n] 标注引用来源;材料不足时明确说明,不要编造。"
)


def _summarize(text: str, limit: int = 100) -> str:
    compact = " ".join((text or "").split())
    return compact if len(compact) <= limit else f"{compact[:limit]}..."


def _build_answer_prompt(state: TutorState) -> str:
    chunks = state.get("retrieved_chunks", [])
    lines = []
    for i, c in enumerate(chunks, start=1):
        meta = c.get("metadata", {})
        loc = meta.get("section") or meta.get("source_path", "")
        lines.append(f"[{i}] ({loc}) {c.get('text', '')[:500]}")
    corpus = "\n".join(lines) if lines else "(无检索材料)"
    # C 画像:按掌握度调深浅
    profile = state.get("mastery_profile") or {}
    depth_hint = ""
    if profile:
        weak = state.get("weak_topics") or []
        depth_hint = (
            f"\n学员薄弱知识点: {', '.join(weak) if weak else '无'};"
            "对薄弱点多做铺垫、由浅入深。"
        )
    # C 画像:按学员自述(背景/目标/偏好难度)调整讲解方式,不改变引用纪律
    depth_hint += _learner_profile_hint(state.get("learner_profile") or {})
    return (
        f"问题: {state.get('rewritten_query') or state.get('query', '')}\n"
        f"课程材料:\n{corpus}{depth_hint}\n"
        "请基于上述材料作答,并在句末标注 [n] 引用。"
    )


# preferred_difficulty → 讲解风格提示(学员偏好,非课程内容)
_DIFFICULTY_STYLE = {
    "easy": "学员偏好循序渐进:多打比方、拆小步骤、避免一次抛太多术语。",
    "medium": "学员偏好适中深度:概念与机制并重,给出关键要点即可。",
    "hard": "学员偏好挑战:可深入原理与权衡,适度追问和延伸。",
}


def _learner_profile_hint(profile: dict) -> str:
    """把学员自述画像拼成讲解提示。空画像返回空串(新学员/访客零影响)。"""
    if not profile:
        return ""
    parts: list[str] = []
    background = (profile.get("background") or "").strip()
    goal = (profile.get("learning_goal") or "").strip()
    difficulty = (profile.get("preferred_difficulty") or "").strip()
    if background:
        parts.append(f"学员背景: {background[:120]};可结合其已有经验类比。")
    if goal:
        parts.append(f"学员学习目标: {goal[:120]};讲解尽量贴合该目标。")
    style = _DIFFICULTY_STYLE.get(difficulty)
    if style:
        parts.append(style)
    return ("\n" + " ".join(parts)) if parts else ""


def _build_citations(chunks: list[dict]) -> list[dict]:
    citations: list[dict] = []
    for i, c in enumerate(chunks, start=1):
        meta = c.get("metadata", {})
        citations.append(
            {
                "citation_id": i,
                "chunk_id": c.get("chunk_id", ""),
                "course_id": meta.get("course_id", ""),
                "section": meta.get("section", ""),
                "source_path": meta.get("source_path", ""),
                "slide_no": meta.get("slide_no"),
                "anchor_type": meta.get("anchor_type", "none"),
                "anchor_value": meta.get("anchor_value", ""),
            }
        )
    return citations


# --- 节点工厂:闭包注入 retriever / llm,便于测试替身 ---


def make_qa_nodes(retriever: Retriever, llm: LLMClient) -> dict[str, Callable]:
    def retrieve(state: TutorState) -> dict:
        query = state.get("rewritten_query") or state.get("query", "")
        # C 画像:按薄弱前置知识点扩展检索(把薄弱点并入检索语义 + 适度扩 top_k)
        weak = state.get("weak_topics") or []
        top_k = state.get("top_k", 5)
        retrieval_query = query
        if weak:
            weak_terms = " ".join(t.replace(".", " ") for t in weak)
            retrieval_query = f"{query} {weak_terms}"
            top_k = min(top_k + len(weak), 20)
        chunks = retriever.retrieve(
            course_pack_id=state.get("course_pack_id", ""),
            query=retrieval_query,
            course_ids=state.get("course_ids") or None,
            top_k=top_k,
        )
        return {
            "retrieved_chunks": chunks,
            "retry_count": state.get("retry_count", 0),
            "trace": append_trace(
                state,
                new_trace_event(
                    "retrieve",
                    input_summary=_summarize(retrieval_query),
                    output_summary=f"chunks={len(chunks)}",
                    attempt=state.get("retry_count", 0),
                    weak_expanded=bool(weak),
                ),
            ),
        }

    def evidence_check(state: TutorState) -> dict:
        chunks = state.get("retrieved_chunks", [])
        top = max((c.get("score", 0.0) for c in chunks), default=0.0)
        if top >= STRONG_EVIDENCE_THRESHOLD:
            level = "strong"
        elif top >= WEAK_EVIDENCE_THRESHOLD:
            level = "weak"
        else:
            level = "insufficient"
        sufficient = level != "insufficient"
        return {
            "evidence_level": level,
            "evidence_score": round(top, 4),
            "evidence_sufficient": sufficient,
            "trace": append_trace(
                state,
                new_trace_event(
                    "evidence_check",
                    output_summary=level,
                    evidence_score=round(top, 4),
                ),
            ),
        }

    def query_rewrite(state: TutorState) -> dict:
        base = state.get("query", "")
        attempt = state.get("retry_count", 0) + 1
        # 真实改写:补全问句 + 追加澄清意图(简化启发式,可换 LLM)
        rewritten = " ".join(base.split())
        if not rewritten.endswith(("?", "？")):
            rewritten += "？"
        rewritten = f"{rewritten} 相关核心概念与定义"
        return {
            "rewritten_query": rewritten,
            "retry_count": attempt,
            "trace": append_trace(
                state,
                new_trace_event(
                    "query_rewrite",
                    input_summary=_summarize(base),
                    output_summary=_summarize(rewritten),
                    attempt=attempt,
                ),
            ),
        }

    def answer(state: TutorState) -> dict:
        chunks = state.get("retrieved_chunks", [])
        prompt = _build_answer_prompt(state)
        # review 判 revise 才会回环到这里;以此为信号计数重生成次数(与
        # query_rewrite 在回环边上计数 retry_count 的写法对齐,route_after_review 据此封顶)
        retry_count = state.get("generate_retry_count", 0)
        if state.get("review_verdict") == "revise":
            retry_count += 1
        try:
            text = llm.complete(prompt, system=_ANSWER_SYSTEM)
        except Exception as exc:  # LLM 失败降级,不炸图
            text = f"（生成失败,基于材料摘要）{chunks[0].get('text', '')[:200] if chunks else ''} [1]"
            return {
                "answer": text,
                "citations": _build_citations(chunks),
                "generate_retry_count": retry_count,
                "trace": append_trace(
                    state, new_trace_event("answer", status="error", output_summary=str(exc)[:80])
                ),
            }
        return {
            "answer": text,
            "citations": _build_citations(chunks),
            "generate_retry_count": retry_count,
            "trace": append_trace(
                state, new_trace_event("answer", output_summary=_summarize(text), attempt=retry_count)
            ),
        }

    def review(state: TutorState) -> dict:
        text = state.get("answer", "")
        has_citation = "[1]" in text or "[" in text
        verdict = "pass" if has_citation else "revise"
        return {
            "review_verdict": verdict,
            "trace": append_trace(state, new_trace_event("review", output_summary=verdict)),
        }

    def final(state: TutorState) -> dict:
        text = state.get("answer", "")
        if state.get("evidence_level") == "weak":
            text = f"证据相对有限,以下基于已检索材料:{text}"
        return {
            "answer": text,
            "refused": False,
            "trace": append_trace(state, new_trace_event("final", output_summary=_summarize(text))),
        }

    def refuse(state: TutorState) -> dict:
        text = "当前课程材料中没有找到足够证据回答这个问题,建议补充材料或换个问法。"
        return {
            "answer": text,
            "refused": True,
            "citations": [],
            "trace": append_trace(
                state, new_trace_event("refuse", output_summary="insufficient_evidence")
            ),
        }

    return {
        "retrieve": retrieve,
        "evidence_check": evidence_check,
        "query_rewrite": query_rewrite,
        "answer": answer,
        "review": review,
        "final": final,
        "refuse": refuse,
    }


# --- 条件边路由函数 ---


def route_after_evidence(state: TutorState) -> str:
    if state.get("evidence_sufficient"):
        return "answer"
    if state.get("retry_count", 0) < state.get("max_retry", 1):
        return "query_rewrite"
    return "refuse"


def route_after_review(state: TutorState) -> str:
    verdict = state.get("review_verdict", "pass")
    if verdict == "pass":
        return "final"
    if verdict == "revise":
        if state.get("generate_retry_count", 0) < state.get("max_generate_retry", 1):
            return "answer"
        # 重生成次数耗尽:直接用现有答案收尾。review 只检查引用格式,不是证据判定,
        # 耗尽不应等同"证据不足"而拒答,否则会丢弃一个基于真实证据生成的合理回答。
        return "final"
    return "refuse"


def build_qa_graph(
    retriever: Retriever,
    llm: LLMClient | None = None,
    compile_graph: bool = True,
):
    """构建问答子图。compile_graph=False 时返回未编译 StateGraph(供检视)。"""
    llm = llm or get_llm_client()
    nodes = make_qa_nodes(retriever, llm)

    g = StateGraph(TutorState)
    for name, fn in nodes.items():
        g.add_node(name, fn)

    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "evidence_check")
    g.add_conditional_edges(
        "evidence_check",
        route_after_evidence,
        {"answer": "answer", "query_rewrite": "query_rewrite", "refuse": "refuse"},
    )
    g.add_edge("query_rewrite", "retrieve")  # 真实回环
    g.add_conditional_edges(
        "review",
        route_after_review,
        {"final": "final", "answer": "answer", "refuse": "refuse"},
    )
    g.add_edge("answer", "review")
    g.add_edge("final", END)
    g.add_edge("refuse", END)

    return g.compile() if compile_graph else g
