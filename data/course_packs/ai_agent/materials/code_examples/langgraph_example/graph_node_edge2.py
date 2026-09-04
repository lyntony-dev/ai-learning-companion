# ============ 案例2：Reducer的作用 ============
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
import operator

print("\n" + "="*50)
print("案例2: Reducer的作用")
print("="*50)

# 定义带Reducer的状态
class ScoreState(TypedDict):
    # 没有reducer：每次覆盖
    player_name: str
    # 有reducer：每次累加
    score: Annotated[int, operator.add]
    # 列表累加
    actions: Annotated[list[str], operator.add]

def level1_node(state: ScoreState):
    """第一关：获得10分"""
    return {
        "score": 10,
        "actions": ["完成第一关"]
    }

def level2_node(state: ScoreState):
    """第二关：获得20分"""
    return {
        "score": 20,
        "actions": ["完成第二关"]
    }

def level3_node(state: ScoreState):
    """第三关：获得30分"""
    return {
        "score": 30,
        "actions": ["完成第三关"]
    }

# 创建图
workflow = StateGraph(ScoreState)
workflow.add_node("level1", level1_node)
workflow.add_node("level2", level2_node)
workflow.add_node("level3", level3_node)

workflow.add_edge(START, "level1")
workflow.add_edge("level1", "level2")
workflow.add_edge("level2", "level3")
workflow.add_edge("level3", END)

app = workflow.compile()

# 运行
result = app.invoke({
    "player_name": "玩家小明",
    "score": 0,
    "actions": []
})

print(f"\n玩家: {result['player_name']}")
print(f"总分: {result['score']}")  # 10+20+30=60（因为有reducer！）
print(f"完成动作: {result['actions']}")

# 如果没有reducer，score会是30（最后一次的值）
# 有了reducer，score是60（累加结果）