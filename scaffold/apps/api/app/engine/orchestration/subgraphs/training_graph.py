"""训练闭环子图 (E) (ADR-0004 / DESIGN §4.3)。

一轮最小训练闭环(真实 StateGraph):

  select_question → grade → update_mastery → END

  - select_question:按薄弱点选/生成题目,写入 State.current_question。
    若 State 未带 learner_answer(尚未作答),走 await_answer 分支直接结束,
    把题目回给学员(交互式训练:先出题,再由下一次请求带作答进来批改)。
  - grade:Grader 按 Rubric 批改 State.learner_answer,写 State.grade_result。
  - update_mastery:写 exercise_attempt + 回写 mastery(可达 known,不覆盖讲师修正)。

领域无关:题目/维度/知识点来自注入的 CoursePack 与题库,不硬编码课程内容。
出题所需的 RAG 证据由注入的 Retriever 提供(题库不足时 LLM 依证据生成)。
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.engine.orchestration.state import TutorState, append_trace, new_trace_event
from app.engine.retrieval import Retriever
from app.engine.training.service import TrainingService


def _summarize(text: str, limit: int = 80) -> str:
    compact = " ".join((text or "").split())
    return compact if len(compact) <= limit else f"{compact[:limit]}..."


def make_training_nodes(
    training: TrainingService, retriever: Retriever | None
) -> dict:
    def select_question(state: TutorState) -> dict:
        weak = state.get("weak_topics") or []
        question = training.select_question(
            learner_id=state.get("learner_id", ""),
            course_pack_id=state.get("course_pack_id", ""),
            weak_topics=weak,
            retriever=retriever,
        )
        return {
            "current_question": question,
            "trace": append_trace(
                state,
                new_trace_event(
                    "select_question",
                    output_summary=_summarize(question.get("prompt", "")),
                    topic_id=question.get("topic_id", ""),
                    source=question.get("source", ""),
                ),
            ),
        }

    def await_answer(state: TutorState) -> dict:
        """未带作答:回题给学员,不批改(交互式训练先出题)。"""
        q = state.get("current_question") or {}
        return {
            "answer": q.get("prompt", "暂无可用题目。"),
            "trace": append_trace(
                state, new_trace_event("await_answer", output_summary="question_issued")
            ),
        }

    def grade(state: TutorState) -> dict:
        question = state.get("current_question") or {}
        result = training.grade(question, state.get("learner_answer", ""))
        return {
            "grade_result": result,
            "trace": append_trace(
                state,
                new_trace_event(
                    "grade",
                    output_summary=f"score={result.get('score')}",
                    passed=result.get("passed"),
                ),
            ),
        }

    def update_mastery(state: TutorState) -> dict:
        question = state.get("current_question") or {}
        grade_result = state.get("grade_result") or {}
        upd = training.update_mastery(
            state.get("learner_id", ""), question, grade_result
        )
        score = grade_result.get("score", 0.0)
        feedback = grade_result.get("feedback", "")
        answer = (
            f"批改完成:得分 {score}。{feedback} "
            f"当前「{question.get('topic_id', '')}」掌握度:{upd.get('level')}。"
        )
        return {
            "answer": answer,
            "trace": append_trace(
                state,
                new_trace_event(
                    "update_mastery",
                    output_summary=f"level={upd.get('level')}",
                    overwritten=upd.get("overwritten"),
                ),
            ),
        }

    return {
        "select_question": select_question,
        "await_answer": await_answer,
        "grade": grade,
        "update_mastery": update_mastery,
    }


def route_after_select(state: TutorState) -> str:
    """带作答 → 批改;未带作答 → 出题即返回(交互式先出题)。"""
    q = state.get("current_question") or {}
    if not q:
        return "await_answer"
    if (state.get("learner_answer") or "").strip():
        return "grade"
    return "await_answer"


def build_training_graph(
    training: TrainingService,
    retriever: Retriever | None = None,
    compile_graph: bool = True,
):
    """构建训练闭环子图。compile_graph=False 返回未编译 StateGraph(供检视)。"""
    nodes = make_training_nodes(training, retriever)

    g = StateGraph(TutorState)
    for name, fn in nodes.items():
        g.add_node(name, fn)

    g.set_entry_point("select_question")
    g.add_conditional_edges(
        "select_question",
        route_after_select,
        {"grade": "grade", "await_answer": "await_answer"},
    )
    g.add_edge("grade", "update_mastery")
    g.add_edge("update_mastery", END)
    g.add_edge("await_answer", END)

    return g.compile() if compile_graph else g
