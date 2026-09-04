# ============================================
# 案例1：最简单的条件路由 - 天气决策
#     START
#       ↓
#   [检查天气]
#       ↓
#  {是否下雨?}  ← 这是决策点！
#     /    \
#    YES   NO
#    ↓      ↓
# [带伞]  [不带伞]
#    \    /
#      ↓
#     END
# ============================================

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Literal

print("=" * 60)
print("案例1：最简单的条件路由 - 天气决策")
print("=" * 60)


# 1. 定义状态
class WeatherState(TypedDict):
    weather: str  # 天气情况
    action: str  # 采取的行动


# 2. 定义节点 - 检查天气
def check_weather_node(state: WeatherState):
    """检查天气节点"""
    weather = state["weather"]
    print(f"\n🌤️  今天天气: {weather}")
    return {}  # 不修改状态，只是检查


# 3. 定义节点 - 带伞
def take_umbrella_node(state: WeatherState):
    """带伞节点"""
    print("☔ 决定: 带伞出门")
    return {"action": "带伞"}


# 4. 定义节点 - 不带伞
def no_umbrella_node(state: WeatherState):
    """不带伞节点"""
    print("☀️  决定: 不带伞")
    return {"action": "不带伞"}


# 5. 【关键】定义路由函数（决策函数）
def decide_umbrella(state: WeatherState) -> Literal["rain", "sunny"]:
    """
    这是决策函数！

    它的作用：根据状态决定下一步去哪个节点

    返回值：
    - "rain" → 会去到"带伞"节点
    - "sunny" → 会去到"不带伞"节点
    """
    weather = state["weather"]

    print(f"\n🤔 决策中...")

    # 决策逻辑（就是普通的if-else）
    if "雨" in weather or "阴" in weather:
        print("   → 判断结果: 可能下雨")
        return "rain"
    else:
        print("   → 判断结果: 不会下雨")
        return "sunny"


# 6. 构建图
workflow = StateGraph(WeatherState)

# 添加节点
workflow.add_node("check", check_weather_node)
workflow.add_node("take_umbrella", take_umbrella_node)
workflow.add_node("no_umbrella", no_umbrella_node)

# 【重点1】普通边：固定的路径
workflow.add_edge(START, "check")

# 【重点2】条件边：根据函数返回值决定路径
workflow.add_conditional_edges(
    "check",  # 从哪个节点开始判断
    decide_umbrella,  # 用哪个函数做决策
    {
        "rain": "take_umbrella",  # 如果返回"rain"，去"take_umbrella"节点
        "sunny": "no_umbrella"  # 如果返回"sunny"，去"no_umbrella"节点
    }
)

# 【重点3】最后都要到END
workflow.add_edge("take_umbrella", END)
workflow.add_edge("no_umbrella", END)

# 编译
app = workflow.compile()

# 7. 测试不同天气
test_cases = [
    {"weather": "下雨", "action": ""},
    {"weather": "晴天", "action": ""},
    {"weather": "阴天", "action": ""},
]

for test in test_cases:
    print(f"\n{'=' * 40}")
    result = app.invoke(test)
    print(f"✅ 最终行动: {result['action']}")
    print("=" * 40)