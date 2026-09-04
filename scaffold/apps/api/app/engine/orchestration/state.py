"""引擎共享状态 TutorState (ADR-0001/0004 / DESIGN §4.1)。

顶层主图与所有子图共享同一 TypedDict。字段按能力块分组:
请求上下文 / 检索 / 生成评审 / 画像(C) / 建议(D) / 训练(E) / 项目(F) / 轨迹。

引擎领域无关:这里不出现任何具体课程常量;course_pack_id 只是标识符,
真实课程内容由 CoursePack 数据注入。
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict


def _keep_last(_old: Any, new: Any) -> Any:
    """reducer:后写覆盖。用于标量字段与显式累积的 trace 的合并语义。"""
    return new


class TutorState(TypedDict, total=False):
    # --- 请求上下文 ---
    learner_id: str
    course_pack_id: str
    query: str
    task_type: str  # rag_answer | direct_answer | grade_homework | capstone
    course_ids: list[str]
    top_k: int

    # --- 检索 ---
    rewritten_query: str
    retrieved_chunks: list[dict]
    citations: list[dict]
    retry_count: int
    max_retry: int
    evidence_sufficient: bool
    evidence_level: str  # strong | weak | insufficient
    evidence_score: float

    # --- 生成 / 评审 ---
    answer: str
    review_verdict: str  # pass | revise | reject
    refused: bool
    generate_retry_count: int  # review=revise 的次数,封顶 max_generate_retry 防止无限重生成
    max_generate_retry: int

    # --- 画像 (C) ---
    mastery_profile: dict
    weak_topics: list[str]
    learner_profile: dict  # 学员自述:background / learning_goal / preferred_difficulty

    # --- 建议 (D) ---
    session_opener: str
    closing_suggestion: str

    # --- 训练 (E) ---
    learner_answer: str  # 学员对 current_question 的作答(批改输入)
    current_question: dict
    grade_result: dict

    # --- 项目 (F) ---
    current_milestone: str
    milestone_verdict: dict

    # --- 轨迹(显式累积:节点返回完整列表,override 合并;避免子图边界重复) ---
    trace: Annotated[list[dict], _keep_last]


def append_trace(state: "TutorState", *events: dict) -> list[dict]:
    """把新事件追加到当前 trace 并返回完整列表(配合 _keep_last 覆盖语义)。

    子图与主图共享 trace 通道时,用 override + 显式累积可避免子图返回值被父图
    再次追加导致的事件重复。
    """
    return [*(state.get("trace") or []), *events]


def new_trace_event(
    node: str,
    status: str = "success",
    input_summary: str = "",
    output_summary: str = "",
    **metadata: Any,
) -> dict:
    """构造一个轨迹事件(节点 IO 可观测)。"""
    return {
        "node": node,
        "status": status,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "metadata": metadata,
    }
