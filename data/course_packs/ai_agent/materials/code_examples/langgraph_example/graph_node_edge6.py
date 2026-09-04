# ============ 完整项目：智能客服系统 ============
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Annotated, Literal
import operator

print("\n" + "=" * 50)
print("完整项目: 智能客服系统")
print("=" * 50)


# 扩展MessagesState
class CustomerServiceState(MessagesState):
    ticket_id: str
    category: str
    priority: Literal["low", "medium", "high"]
    satisfaction_score: int
    resolved: bool


# 节点1: 问题分类
def classify_issue(state: CustomerServiceState):
    """分类客户问题"""
    last_msg = state["messages"][-1].content.lower()

    if any(word in last_msg for word in ["紧急", "无法使用", "崩溃"]):
        category, priority = "technical", "high"
    elif any(word in last_msg for word in ["退款", "退货"]):
        category, priority = "refund", "medium"
    elif any(word in last_msg for word in ["账单", "费用"]):
        category, priority = "billing", "medium"
    else:
        category, priority = "general", "low"

    ticket_id = f"TKT-{hash(last_msg) % 10000:04d}"

    print(f"\n📋 工单创建:")
    print(f"  工单号: {ticket_id}")
    print(f"  类别: {category}")
    print(f"  优先级: {priority}")

    return {
        "ticket_id": ticket_id,
        "category": category,
        "priority": priority
    }


# 节点2-4: 不同类别的处理
def handle_technical(state: CustomerServiceState):
    """处理技术问题"""
    response = f"""
🔧 技术支持团队已接手工单 {state['ticket_id']}

我们的工程师将在2小时内响应。请提供以下信息：
1. 设备型号
2. 系统版本
3. 错误截图

临时解决方案：尝试清除缓存并重启应用。
    """
    return {
        "messages": [AIMessage(content=response.strip())],
        "resolved": False
    }


def handle_refund(state: CustomerServiceState):
    """处理退款问题"""
    response = f"""
💰 退款部门已接收工单 {state['ticket_id']}

退款流程：
1. 请提供订单号
2. 说明退款原因
3. 我们将在3个工作日内处理

预计退款时间：5-7个工作日到账
    """
    return {
        "messages": [AIMessage(content=response.strip())],
        "resolved": False
    }


def handle_general(state: CustomerServiceState):
    """处理一般问题"""
    response = f"""
ℹ️ 客服团队已接收工单 {state['ticket_id']}

感谢您的咨询！我们会尽快回复。
同时，您可以访问我们的帮助中心获取更多信息。
    """
    return {
        "messages": [AIMessage(content=response.strip())],
        "resolved": True
    }


# 节点5: 满意度调查
def satisfaction_survey(state: CustomerServiceState):
    """满意度调查"""
    response = """
📊 请为本次服务打分（1-5分）：
1 - 非常不满意
2 - 不满意
3 - 一般
4 - 满意
5 - 非常满意
    """
    return {"messages": [AIMessage(content=response.strip())]}


# 路由函数
def route_by_category(state: CustomerServiceState) -> str:
    """根据类别路由"""
    category = state["category"]

    route_map = {
        "technical": "technical",
        "refund": "refund",
        "billing": "refund",  # billing也走refund流程
        "general": "general"
    }

    return route_map.get(category, "general")


def check_if_resolved(state: CustomerServiceState) -> str:
    """检查是否已解决"""
    if state.get("resolved", False):
        return "survey"
    return "done"


# 构建图
workflow = StateGraph(CustomerServiceState)

# 添加所有节点
workflow.add_node("classify", classify_issue)
workflow.add_node("technical", handle_technical)
workflow.add_node("refund", handle_refund)
workflow.add_node("general", handle_general)
workflow.add_node("survey", satisfaction_survey)

# 构建流程
workflow.add_edge(START, "classify")

# 条件路由：根据类别分发
workflow.add_conditional_edges(
    "classify",
    route_by_category,
    {
        "technical": "technical",
        "refund": "refund",
        "general": "general"
    }
)

# 所有处理完后检查是否需要调查
workflow.add_conditional_edges(
    "technical",
    check_if_resolved,
    {"survey": "survey", "done": END}
)
workflow.add_conditional_edges(
    "refund",
    check_if_resolved,
    {"survey": "survey", "done": END}
)
workflow.add_conditional_edges(
    "general",
    check_if_resolved,
    {"survey": "survey", "done": END}
)

workflow.add_edge("survey", END)

# 编译
app = workflow.compile()

# 测试不同类型的问题
test_cases = [
    "应用崩溃了，紧急！无法使用！",
    "我要申请退款",
    "你们的服务怎么样？"
]

for i, question in enumerate(test_cases, 1):
    print(f"\n{'=' * 50}")
    print(f"测试案例 {i}: {question}")
    print("=" * 50)

    result = app.invoke({
        "messages": [HumanMessage(content=question)],
        "ticket_id": "",
        "category": "",
        "priority": "low",
        "satisfaction_score": 0,
        "resolved": False
    })

    print(f"\n📬 客服回复:")
    for msg in result["messages"][1:]:  # 跳过用户消息
        print(msg.content)

    print(f"\n📊 工单状态:")
    print(f"  优先级: {result['priority']}")
    print(f"  是否解决: {result['resolved']}")