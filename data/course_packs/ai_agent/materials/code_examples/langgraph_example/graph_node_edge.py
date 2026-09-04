"""
案例1：计数器 - 理解状态流转
目标：创建一个简单的计数器，理解状态如何在节点间传递
"""
# ============ 案例1：简单计数器 ============
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

print("=" * 50)
print("案例1: 简单计数器")
print("=" * 50)


# 1. 定义状态结构
class CounterState(TypedDict):
    count: int
    history: list[str]


# 2. 定义节点函数
def increment_node(state: CounterState):
    """每次调用，计数器+1"""
    new_count = state["count"] + 1
    message = f"节点执行: count从 {state['count']} 增加到 {new_count}"

    # 注意：只返回需要更新的字段！
    return {
        "count": new_count,
        "history": state["history"] + [message]
    }


def double_node(state: CounterState):
    """计数器翻倍"""
    new_count = state["count"] * 2
    message = f"节点执行: count从 {state['count']} 翻倍到 {new_count}"

    return {
        "count": new_count,
        "history": state["history"] + [message]
    }


def report_node(state: CounterState):
    """报告最终结果"""
    message = f"最终结果: count = {state['count']}"
    return {"history": state["history"] + [message]}


# 3. 创建图
workflow = StateGraph(CounterState)

# 4. 添加节点
workflow.add_node("increment", increment_node)
workflow.add_node("double", double_node)
workflow.add_node("report", report_node)

# 5. 连接节点（定义执行流程）
workflow.add_edge(START, "increment")
workflow.add_edge("increment", "double")
workflow.add_edge("double", "report")
workflow.add_edge("report", END)

# 6. 编译图
app = workflow.compile()

# 7. 运行图
initial_state = {
    "count": 5,
    "history": ["开始执行"]
}

result = app.invoke(initial_state)

print("\n执行历史:")
for step in result["history"]:
    print(f"  - {step}")
print(f"\n最终计数: {result['count']}")

# 预期输出:
# count: 5 -> 6 (increment) -> 12 (double) -> 12 (report)
