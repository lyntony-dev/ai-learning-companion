# ============================================
# 案例2：多选一路由 - 餐厅点餐
# ============================================

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Literal

print("\n" + "=" * 60)
print("案例2：多选一路由 - 餐厅点餐")
print("=" * 60)


# 1. 定义状态
class OrderState(TypedDict):
    customer_choice: str  # 顾客选择
    dish: str  # 最终菜品


# 2. 看菜单节点
def show_menu_node(state: OrderState):
    """展示菜单"""
    choice = state["customer_choice"]
    print(f"\n👨‍🍳 服务员: 您点的是 '{choice}'")
    return {}


# 3. 准备不同食物的节点
def cook_noodles_node(state: OrderState):
    """煮面"""
    print("🍜 厨师: 正在煮面...")
    return {"dish": "热腾腾的拉面"}


def cook_rice_node(state: OrderState):
    """煮饭"""
    print("🍚 厨师: 正在煮饭...")
    return {"dish": "香喷喷的米饭"}


def bake_bread_node(state: OrderState):
    """烤面包"""
    print("🍞 厨师: 正在烤面包...")
    return {"dish": "金黄的面包"}


def default_node(state: OrderState):
    """默认选项"""
    print("❓ 厨师: 不好意思，我们没有这个菜")
    return {"dish": "推荐今日特餐"}


# 4. 【关键】路由函数 - 多选一
def route_to_kitchen(state: OrderState) -> Literal["noodles", "rice", "bread", "default"]:
    """
    根据顾客选择路由到不同的厨房

    返回值有4种可能：
    - "noodles" → 煮面
    - "rice" → 煮饭
    - "bread" → 烤面包
    - "default" → 默认
    """
    choice = state["customer_choice"].lower()

    print(f"🤔 判断中: '{choice}'")

    # 多个if-elif判断
    if "面" in choice or "noodle" in choice:
        print("   → 去面条厨房")
        return "noodles"

    elif "饭" in choice or "rice" in choice:
        print("   → 去米饭厨房")
        return "rice"

    elif "面包" in choice or "bread" in choice:
        print("   → 去烘焙厨房")
        return "bread"

    else:
        print("   → 去默认厨房")
        return "default"


# 5. 构建图
workflow = StateGraph(OrderState)

# 添加所有节点
workflow.add_node("menu", show_menu_node)
workflow.add_node("cook_noodles", cook_noodles_node)
workflow.add_node("cook_rice", cook_rice_node)
workflow.add_node("bake_bread", bake_bread_node)
workflow.add_node("default_meal", default_node)

# 普通边
workflow.add_edge(START, "menu")

# 【关键】条件边 - 四选一
workflow.add_conditional_edges(
    "menu",  # 从menu节点判断
    route_to_kitchen,  # 使用route_to_kitchen函数决策
    {
        "noodles": "cook_noodles",  # 返回"noodles"→去cook_noodles
        "rice": "cook_rice",  # 返回"rice"→去cook_rice
        "bread": "bake_bread",  # 返回"bread"→去bake_bread
        "default": "default_meal"  # 返回"default"→去default_meal
    }
)

# 所有节点最后都到END
workflow.add_edge("cook_noodles", END)
workflow.add_edge("cook_rice", END)
workflow.add_edge("bake_bread", END)
workflow.add_edge("default_meal", END)

# 编译
app = workflow.compile()

# 6. 测试不同点餐
orders = [
    {"customer_choice": "我要一碗面", "dish": ""},
    {"customer_choice": "来份米饭", "dish": ""},
    {"customer_choice": "烤面包", "dish": ""},
    {"customer_choice": "披萨", "dish": ""},
]

for order in orders:
    print(f"\n{'=' * 50}")
    result = app.invoke(order)
    print(f"✅ 最终上菜: {result['dish']}")
    print("=" * 50)