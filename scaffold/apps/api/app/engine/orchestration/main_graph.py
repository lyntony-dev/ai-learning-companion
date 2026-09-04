"""顶层 Router 主图 (ADR-0004 / DESIGN §4.2)。

结构:
  personalize_opener(C+D 进入装饰)
    → router(意图路由)
      ─(rag_answer/direct_answer)→ qa_subgraph
      ─(grade_homework)→ training_subgraph
      ─(capstone)→ capstone_subgraph
    → closing_advice(D 退出装饰) → END

本轮纵切真实贯通:opener → router → qa_subgraph → closing。
训练/项目子图本轮为最小可运行占位(feat-007/008 填充),路由已就绪。
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.engine.learner_model import EmptyLearnerModel, LearnerModel
from app.engine.orchestration.decorators.personalization import (
    closing_advice,
    make_personalization_opener,
)
from app.engine.orchestration.state import TutorState, append_trace, new_trace_event
from app.engine.orchestration.subgraphs.qa_graph import build_qa_graph
from app.engine.orchestration.subgraphs.training_graph import build_training_graph
from app.engine.retrieval import Retriever
from app.engine.training import TrainingService
from app.llm import LLMClient, get_llm_client

_QA_TASKS = {"rag_answer", "direct_answer"}


def router_node(state: TutorState) -> dict:
    """意图路由:归一 task_type(缺省按 rag_answer)。"""
    task = state.get("task_type") or "rag_answer"
    if not state.get("query", "").strip() and task in _QA_TASKS:
        task = "direct_answer"
    return {
        "task_type": task,
        "trace": append_trace(state, new_trace_event("router", output_summary=task)),
    }


def route_by_task(state: TutorState) -> str:
    task = state.get("task_type", "rag_answer")
    if task in _QA_TASKS:
        return "qa"
    if task == "grade_homework":
        return "training"
    if task == "capstone":
        return "capstone"
    return "qa"


def _stub_subgraph(name: str, message: str):
    """训练/项目子图占位:合法节点,产出提示,feat-007/008 替换为真子图。"""

    def node(state: TutorState) -> dict:
        return {
            "answer": message,
            "trace": append_trace(state, new_trace_event(name, output_summary="stub")),
        }

    g = StateGraph(TutorState)
    g.add_node(name, node)
    g.set_entry_point(name)
    g.add_edge(name, END)
    return g.compile()


def build_main_graph(
    retriever: Retriever,
    llm: LLMClient | None = None,
    learner_model: LearnerModel | None = None,
    training_service: TrainingService | None = None,
    checkpointer=None,
    compile_graph: bool = True,
):
    """构建顶层主图。

    learner_model 同时承担:
      - C/D 读:profile()/weak_topics() 供画像装饰(检索扩展 + 答复深浅)。
      - B 写:record_qa_turn() 在问答后沉淀掌握度/问答历史。
    training_service 承担 E 训练闭环(出题→批改→更新掌握度);缺省时训练子图为占位。
    项目立项(F)已从主图剥离,改由 REST 路由(立项向导 + 个性化清单)承载;项目子图保留占位。
    checkpointer 可传 LangGraph SqliteSaver 做会话持久化。
    """
    llm = llm or get_llm_client()
    learner_model = learner_model or EmptyLearnerModel()

    qa_sub = build_qa_graph(retriever, llm)
    if training_service is not None:
        training_sub = build_training_graph(training_service, retriever)
    else:
        training_sub = _stub_subgraph(
            "training", "训练闭环子图(需注入 training_service):将出题→批改→更新掌握度。"
        )
    capstone_sub = _stub_subgraph(
        "capstone", "项目立项已改由 REST 路由(立项向导 + 个性化清单)承载,主图不再走此子图。"
    )

    def learner_update(state: TutorState) -> dict:
        """B:问答结果反哺 Learner Model(掌握度/问答历史)。"""
        result = learner_model.record_qa_turn(dict(state))
        return {
            "trace": append_trace(
                state,
                new_trace_event(
                    "learner_update",
                    output_summary=f"touched={len(result.get('touched_topics', []))}",
                    mastery_updates=result.get("mastery_updates", 0),
                ),
            ),
        }

    g = StateGraph(TutorState)
    g.add_node("personalize_opener", make_personalization_opener(learner_model))
    g.add_node("router", router_node)
    g.add_node("qa", qa_sub)
    g.add_node("training", training_sub)
    g.add_node("capstone", capstone_sub)
    g.add_node("learner_update", learner_update)
    g.add_node("closing_advice", closing_advice)

    g.set_entry_point("personalize_opener")
    g.add_edge("personalize_opener", "router")
    g.add_conditional_edges(
        "router",
        route_by_task,
        {"qa": "qa", "training": "training", "capstone": "capstone"},
    )
    # 问答后经 B 掌握度更新再收尾(A→B→…→D);训练/项目子图自身更新掌握度
    g.add_edge("qa", "learner_update")
    g.add_edge("learner_update", "closing_advice")
    g.add_edge("training", "closing_advice")
    g.add_edge("capstone", "closing_advice")
    g.add_edge("closing_advice", END)

    if not compile_graph:
        return g
    if checkpointer is not None:
        return g.compile(checkpointer=checkpointer)
    return g.compile()


def initial_state(
    query: str,
    course_pack_id: str,
    learner_id: str = "demo_user",
    task_type: str = "rag_answer",
    course_ids: list[str] | None = None,
    top_k: int = 5,
    max_retry: int = 1,
    max_generate_retry: int = 1,
    learner_answer: str = "",
) -> TutorState:
    """构造一次调用的初始 TutorState。

    learner_answer 用于 E 训练闭环:带作答则批改,不带则出题返回(交互式训练)。
    max_generate_retry 封顶 qa_graph 的 answer↔review 重生成循环(见 qa_graph.route_after_review)。
    """
    return {
        "query": query,
        "course_pack_id": course_pack_id,
        "learner_id": learner_id,
        "task_type": task_type,
        "course_ids": course_ids or [],
        "top_k": top_k,
        "retry_count": 0,
        "max_retry": max_retry,
        "generate_retry_count": 0,
        "max_generate_retry": max_generate_retry,
        "learner_answer": learner_answer,
        "trace": [],
    }
