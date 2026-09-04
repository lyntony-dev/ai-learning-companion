# ============ 案例4：循环改进 ============
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
import operator

print("\n" + "=" * 50)
print("案例4: 循环改进 - 答案优化器")
print("=" * 50)


# 定义状态
class ImprovementState(TypedDict):
    question: str
    answer: str
    quality_score: float
    iteration: Annotated[int, operator.add]
    max_iterations: int


def generate_answer(state: ImprovementState):
    """生成或改进答案"""
    iteration = state.get("iteration", 0)

    # 模拟答案改进（实际应该调用LLM）
    if iteration == 0:
        answer = "简单回答：这是一个答案。"
        score = 0.5
    elif iteration == 1:
        answer = "改进回答：这是一个更详细的答案，包含了更多信息。"
        score = 0.7
    else:
        answer = "完善回答：这是一个经过仔细思考的完整答案，包含了背景、细节和建议。"
        score = 0.9

    print(f"\n第{iteration + 1}次生成 (质量: {score})")
    print(f"答案: {answer}")

    return {
        "answer": answer,
        "quality_score": score,
        "iteration": 1  # 每次+1
    }


def check_quality(state: ImprovementState):
    """检查质量并决定是否继续改进"""
    # 这个节点不返回任何更新，只用于路由
    return state


def route_based_on_quality(state: ImprovementState) -> str:
    """决定是继续改进还是结束"""
    # 如果质量够好，或达到最大迭代次数，就结束
    if state["quality_score"] >= 0.8:
        print("→ 质量达标，结束改进")
        return "done"
    elif state["iteration"] >= state["max_iterations"]:
        print("→ 达到最大迭代次数，结束改进")
        return "done"
    else:
        print("→ 质量不够，继续改进")
        return "improve"


# 构建图
workflow = StateGraph(ImprovementState)

workflow.add_node("generate", generate_answer)
workflow.add_node("check", check_quality)

# 关键：形成循环
workflow.add_edge(START, "generate")
workflow.add_edge("generate", "check")

# 条件边：可能循环回generate，也可能结束
workflow.add_conditional_edges(
    "check",
    route_based_on_quality,
    {
        "improve": "generate",  # 循环回去
        "done": END  # 结束
    }
)

app = workflow.compile()

# 运行
result = app.invoke({
    "question": "什么是人工智能？",
    "answer": "",
    "quality_score": 0.0,
    "iteration": 0,
    "max_iterations": 5
})

print("\n" + "=" * 30)
print(f"最终答案: {result['answer']}")
print(f"最终质量: {result['quality_score']}")
print(f"总迭代次数: {result['iteration']}")

# ** 流程图（带循环）： **
# ```
# START
# ↓
# [generate] ←─┐
# ↓        │
# [check]     │
# ↓        │
# {quality?}    │
# /     \      │
# done
# improve──┘
# ↓
# END