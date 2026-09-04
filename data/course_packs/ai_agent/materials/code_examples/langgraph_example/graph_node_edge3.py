# ============ 案例3：条件分支 ============
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

print("\n" + "=" * 50)
print("案例3: 条件分支 - 智能客服路由")
print("=" * 50)


# 定义状态
class CustomerState(TypedDict):
    question: str
    category: str
    answer: str

"""
LangGraph 中，每个节点的返回值会与当前的全局状态进行合并（而非直接替换整个状态）。具体来说：
如果节点返回 {"category": "refund"}，则全局状态中 category 字段会被更新为 "refund"，
而 question、answer 等其他字段会保持不变（沿用之前的值）。
如果节点返回 {"answer": "xxx"}，则仅 answer 字段被更新，question、category 仍保留之前的状态。
"""
# 1. 分类节点
def classify_question(state: CustomerState):
    """识别问题类别"""
    question = state["question"].lower()

    if "退款" in question or "退货" in question:
        category = "refund"
    elif "物流" in question or "配送" in question:
        category = "shipping"
    elif "产品" in question or "使用" in question:
        category = "product"
    else:
        category = "general"

    print(f"问题分类: {category}")
    return {"category": category}


# 2. 不同类别的处理节点
def handle_refund(state: CustomerState):
    """处理退款问题"""
    return {"answer": "退款专员：请提供订单号，我们将在3个工作日内处理退款。"}


def handle_shipping(state: CustomerState):
    """处理物流问题"""
    return {"answer": "物流客服：您的包裹正在配送中，预计明天送达。"}


def handle_product(state: CustomerState):
    """处理产品问题"""
    return {"answer": "产品顾问：请查看产品说明书第3页，有详细的使用指南。"}


def handle_general(state: CustomerState):
    """处理一般问题"""
    return {"answer": "客服：感谢咨询，请问还有其他问题吗？"}


# 3. 路由函数（关键！）
def route_question(state: CustomerState) -> str:
    """根据类别决定下一个节点"""
    return state["category"]


# 4. 构建图
workflow = StateGraph(CustomerState)

# 添加所有节点
workflow.add_node("classify", classify_question)
workflow.add_node("refund", handle_refund)
workflow.add_node("shipping", handle_shipping)
workflow.add_node("product", handle_product)
workflow.add_node("general", handle_general)

# 关键：添加条件边
workflow.add_edge(START, "classify")
workflow.add_conditional_edges(
    "classify",  # 从classify节点出发
    route_question,  # 使用route_question决定路径
    {
        "refund": "refund",
        "shipping": "shipping",
        "product": "product",
        "general": "general"
    }
)

# 所有分支最终都到END
workflow.add_edge("refund", END)
workflow.add_edge("shipping", END)
workflow.add_edge("product", END)
workflow.add_edge("general", END)

app = workflow.compile()

# 测试不同问题
test_questions = [
    "我想申请退款",
    "我的快递到哪了？",
    "这个产品怎么使用？",
    "你好"
]

for q in test_questions:
    print(f"\n问题: {q}")
    result = app.invoke({
        "question": q,
        "category": "",
        "answer": ""
    })
    print(f"回答: {result['answer']}")

# answer
# ** 流程图： **
# ```
# START
# ↓
# [classify]  ← 分类问题
# ↓
# {route_question}  ← 决策点
# / | | \
#     refund
# ship
# prod
# general
# \ | | /
# ↓
# END