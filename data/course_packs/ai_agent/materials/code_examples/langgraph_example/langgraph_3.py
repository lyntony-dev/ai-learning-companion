# ============================================
# 案例3：多智能体协作 - 专业客服团队
# ============================================

import os
from typing import Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.llms import Tongyi

print("\n" + "=" * 60)
print("案例3: 多智能体协作 - 专业客服团队")
print("=" * 60)

os.environ["DASHSCOPE_API_KEY"] = ""

# 1. 初始化不同的Qwen实例（模拟不同专家）
router_llm = Tongyi(model="qwen-turbo", temperature=0.3)  # 路由器：低温度，更确定
tech_llm = Tongyi(model="qwen-plus", temperature=0.7)  # 技术专家
sales_llm = Tongyi(model="qwen-plus", temperature=0.8)  # 销售专家
support_llm = Tongyi(model="qwen-turbo", temperature=0.7)  # 客服专家


# 2. 定义状态
class TeamState(MessagesState):
    category: str  # 问题类别
    assigned_expert: str  # 分配的专家
    resolved: bool  # 是否解决


# 3. 路由节点 - 分类问题
def router_node(state: TeamState):
    """路由器：识别问题类型并分配专家"""

    user_question = state["messages"][-1].content

    prompt = f"""你是一个客服路由器。根据用户问题，判断应该分配给哪个部门：
- technical: 技术问题（bug、错误、功能不work等）
- sales: 销售问题（价格、购买、套餐等）
- support: 一般客服（账号、密码、使用咨询等）

用户问题：{user_question}

只返回一个词：technical、sales 或 support"""

    category = router_llm.invoke(prompt).strip().lower()

    # 确保返回有效类别
    if category not in ["technical", "sales", "support"]:
        category = "support"

    print(f"\n🎯 路由决策: {category}")

    return {
        "category": category,
        "assigned_expert": category
    }


# 4. 技术专家节点
def technical_expert_node(state: TeamState):
    """技术专家：处理技术问题"""

    user_question = state["messages"][-1].content

    prompt = f"""你是一位资深技术支持工程师。用户遇到了技术问题。

用户问题：{user_question}

请提供专业的技术支持，包括：
1. 问题诊断
2. 可能的原因
3. 详细的解决步骤
4. 预防措施

用中文回答，专业且易懂。"""

    response = tech_llm.invoke(prompt)

    print(f"\n🔧 技术专家回复...")

    return {
        "messages": [AIMessage(content=f"【技术支持】\n\n{response}")],
        "resolved": True
    }


# 5. 销售专家节点
def sales_expert_node(state: TeamState):
    """销售专家：处理销售问题"""

    user_question = state["messages"][-1].content

    prompt = f"""你是一位专业的销售顾问。用户咨询销售相关问题。

用户问题：{user_question}

请提供：
1. 产品/服务介绍
2. 价格方案
3. 优惠活动
4. 购买建议

用热情、专业的语气回答。"""

    response = sales_llm.invoke(prompt)

    print(f"\n💰 销售专家回复...")

    return {
        "messages": [AIMessage(content=f"【销售顾问】\n\n{response}")],
        "resolved": True
    }


# 6. 客服专家节点
def support_expert_node(state: TeamState):
    """客服专家：处理一般问题"""

    user_question = state["messages"][-1].content

    prompt = f"""你是一位友好的客服专员。用户需要帮助。

用户问题：{user_question}

请提供友好、清晰的帮助，包括：
1. 理解用户需求
2. 提供解决方案
3. 额外的使用建议

保持温暖、耐心的语气。"""

    response = support_llm.invoke(prompt)

    print(f"\n💁 客服专家回复...")

    return {
        "messages": [AIMessage(content=f"【客户服务】\n\n{response}")],
        "resolved": True
    }


# 7. 路由函数
def route_to_expert(state: TeamState) -> Literal["technical", "sales", "support"]:
    """根据分类路由到对应专家"""
    return state["category"]


# 8. 构建图
workflow = StateGraph(TeamState)

# 添加节点
workflow.add_node("router", router_node)
workflow.add_node("technical", technical_expert_node)
workflow.add_node("sales", sales_expert_node)
workflow.add_node("support", support_expert_node)

# 构建流程
workflow.add_edge(START, "router")
workflow.add_conditional_edges(
    "router",
    route_to_expert,
    {
        "technical": "technical",
        "sales": "sales",
        "support": "support"
    }
)

# 所有专家都指向END
workflow.add_edge("technical", END)
workflow.add_edge("sales", END)
workflow.add_edge("support", END)

app = workflow.compile()

# 9. 测试不同类型的问题
test_cases = [
    "我的应用崩溃了，一直报错500",
    "你们的VIP套餐多少钱？有什么优惠吗？",
    "我忘记密码了，怎么重置？"
]

for question in test_cases:
    print(f"\n{'=' * 60}")
    print(f"👤 用户提问: {question}")
    print("=" * 60)

    result = app.invoke({
        "messages": [HumanMessage(content=question)],
        "category": "",
        "assigned_expert": "",
        "resolved": False
    })

    # 打印专家回复
    expert_response = result["messages"][-1].content
    print(f"\n{expert_response}")
    print(f"\n状态: {'✅ 已解决' if result['resolved'] else '❌ 未解决'}")