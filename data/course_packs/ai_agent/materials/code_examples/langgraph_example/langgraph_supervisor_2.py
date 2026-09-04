# ============================================
# 完整案例：Supervisor模式 - 智能客户服务系统
# ============================================

import os
import operator
from typing import Annotated, Literal, TypedDict, Sequence
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import add_messages
from langchain_community.llms import Tongyi
import json

print("="*70)
print("Supervisor模式：智能客户服务系统")
print("="*70)

# ============================================
# 第一步：设置环境
# ============================================
os.environ["DASHSCOPE_API_KEY"] = ""

# ============================================
# 第二步：定义State
# ============================================
class SupervisorState(TypedDict):
    """监督者状态"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: str  # 下一个要执行的智能体

# ============================================
# 第三步：为每个专业Agent定义工具
# ============================================

# 技术支持工具
@tool
def check_system_status(component: str) -> str:
    """检查系统组件状态
    
    Args:
        component: 组件名称 (database, server, api)
    """
    status_db = {
        "database": "✅ 数据库运行正常，响应时间 < 10ms",
        "server": "⚠️ 服务器负载较高 (CPU 85%)",
        "api": "✅ API服务正常，所有端点可访问"
    }
    return status_db.get(component, f"{component} 状态未知")

@tool
def search_error_code(error_code: str) -> str:
    """查询错误代码含义
    
    Args:
        error_code: 错误代码
    """
    error_db = {
        "500": "内部服务器错误 - 请联系技术团队",
        "404": "资源未找到 - 请检查URL",
        "403": "访问被拒绝 - 请检查权限",
        "401": "未授权 - 请先登录"
    }
    return error_db.get(error_code, "错误代码未在数据库中")

# 销售工具
@tool
def get_product_info(product_name: str) -> str:
    """获取产品信息
    
    Args:
        product_name: 产品名称
    """
    products = {
        "基础版": "价格：99元/月 | 功能：基础AI对话 | 限制：100次/天",
        "专业版": "价格：299元/月 | 功能：高级AI+工具调用 | 限制：1000次/天",
        "企业版": "价格：999元/月 | 功能：无限制+专属支持 | 限制：无"
    }
    return products.get(product_name, "产品不存在")

@tool
def check_promotion(product: str) -> str:
    """查询当前优惠活动
    
    Args:
        product: 产品名称
    """
    return f"🎉 {product}当前优惠：首月5折！立即订阅可享受此优惠。"

@tool
def calculate_price(product: str, months: int) -> str:
    """计算订阅价格
    
    Args:
        product: 产品名称
        months: 订阅月数
    """
    prices = {"基础版": 99, "专业版": 299, "企业版": 999}
    base_price = prices.get(product, 0)
    
    # 计算折扣
    discount = 0.5 if months >= 12 else 0.8 if months >= 6 else 1.0
    total = base_price * months * discount
    
    return f"💰 {product} {months}个月：原价 {base_price * months}元，折后 {total}元"

# 账单工具
@tool
def query_invoice(order_id: str) -> str:
    """查询发票信息
    
    Args:
        order_id: 订单号
    """
    invoices = {
        "ORD001": "发票已开具 | 金额：299元 | 状态：已发送到邮箱",
        "ORD002": "发票处理中 | 预计3个工作日内完成",
        "ORD003": "发票信息有误 | 请联系财务部门"
    }
    return invoices.get(order_id, "订单号不存在")

@tool
def check_payment_status(transaction_id: str) -> str:
    """查询支付状态
    
    Args:
        transaction_id: 交易ID
    """
    payments = {
        "PAY001": "✅ 支付成功 | 金额：299元 | 时间：2025-01-15 10:30",
        "PAY002": "⏳ 支付处理中 | 预计5分钟内完成",
        "PAY003": "❌ 支付失败 | 原因：余额不足"
    }
    return payments.get(transaction_id, "交易ID不存在")

@tool
def request_refund(order_id: str, reason: str) -> str:
    """申请退款
    
    Args:
        order_id: 订单号
        reason: 退款原因
    """
    return f"✅ 退款申请已提交 | 订单：{order_id} | 原因：{reason} | 预计3-5个工作日处理"

# ============================================
# 第四步：创建专业Agent
# ============================================

# 模拟Qwen模型（实际使用时替换为真实的ChatTongyi）
class MockQwenLLM:
    """模拟支持工具调用的Qwen"""
    def __init__(self, name: str, system_prompt: str):
        self.llm = Tongyi(model="qwen-plus", temperature=0.7)
        self.name = name
        self.system_prompt = system_prompt
    
    def invoke(self, messages):
        # 构建完整提示
        full_prompt = f"{self.system_prompt}\n\n用户消息：{messages[-1].content if messages else ''}"
        response = self.llm.invoke(full_prompt)
        return AIMessage(content=response)

# 创建技术支持Agent
tech_llm = MockQwenLLM(
    "技术支持",
    "你是技术支持专员。专注于解决技术问题、系统错误和故障排查。使用专业的技术语言。"
)

tech_tools = [check_system_status, search_error_code]

def tech_agent_node(state: SupervisorState):
    """技术支持Agent节点"""
    print("\n🔧 技术支持Agent工作中...")
    
    # 获取最后一条消息
    last_message = state["messages"][-1].content
    
    # 简单的工具选择逻辑（实际应该用LLM判断）
    response_parts = []
    
    if "错误" in last_message or "error" in last_message.lower():
        # 查找错误代码
        for code in ["500", "404", "403", "401"]:
            if code in last_message:
                result = search_error_code.invoke({"error_code": code})
                response_parts.append(result)
                break
    
    if "系统" in last_message or "服务器" in last_message:
        # 检查系统状态
        result = check_system_status.invoke({"component": "server"})
        response_parts.append(result)
    
    if not response_parts:
        response_parts.append("我是技术支持，请描述您遇到的技术问题，我会帮您解决。")
    
    response = "\n".join(response_parts)
    return {"messages": [AIMessage(content=f"【技术支持】\n{response}")]}

# 创建销售Agent
sales_tools = [get_product_info, check_promotion, calculate_price]

def sales_agent_node(state: SupervisorState):
    """销售顾问Agent节点"""
    print("\n💼 销售顾问Agent工作中...")
    
    last_message = state["messages"][-1].content
    response_parts = []
    
    # 检查产品咨询
    products = ["基础版", "专业版", "企业版"]
    for product in products:
        if product in last_message:
            info = get_product_info.invoke({"product_name": product})
            promo = check_promotion.invoke({"product": product})
            response_parts.append(info)
            response_parts.append(promo)
            break
    
    # 价格计算
    if "价格" in last_message or "多少钱" in last_message:
        if not response_parts:
            response_parts.append("我们有基础版(99元/月)、专业版(299元/月)、企业版(999元/月)三种套餐。")
    
    if not response_parts:
        response_parts.append("您好！我是销售顾问，很高兴为您介绍我们的产品和优惠活动。")
    
    response = "\n".join(response_parts)
    return {"messages": [AIMessage(content=f"【销售顾问】\n{response}")]}

# 创建账单Agent
billing_tools = [query_invoice, check_payment_status, request_refund]

def billing_agent_node(state: SupervisorState):
    """账单专员Agent节点"""
    print("\n💳 账单专员Agent工作中...")
    
    last_message = state["messages"][-1].content
    response_parts = []
    
    # 发票查询
    if "发票" in last_message:
        response_parts.append("请提供您的订单号，我将为您查询发票状态。示例订单号：ORD001")
        
        # 如果包含订单号
        for order_id in ["ORD001", "ORD002", "ORD003"]:
            if order_id in last_message:
                result = query_invoice.invoke({"order_id": order_id})
                response_parts[-1] = result
                break
    
    # 支付查询
    if "支付" in last_message:
        response_parts.append("请提供交易ID，我将为您查询支付状态。")
        
        for pay_id in ["PAY001", "PAY002", "PAY003"]:
            if pay_id in last_message:
                result = check_payment_status.invoke({"transaction_id": pay_id})
                response_parts[-1] = result
                break
    
    # 退款
    if "退款" in last_message:
        response_parts.append("我理解您需要退款。请告诉我订单号和退款原因，我会立即为您处理。")
    
    if not response_parts:
        response_parts.append("您好！我是账单专员，可以帮您处理发票、支付和退款等财务问题。")
    
    response = "\n".join(response_parts)
    return {"messages": [AIMessage(content=f"【账单专员】\n{response}")]}

# ============================================
# 第五步：创建Supervisor（监督者）
# ============================================

def supervisor_node(state: SupervisorState):
    """监督者节点：决定下一步"""
    
    print("\n👔 Supervisor分析中...")
    
    # 获取最后一条消息
    messages = state["messages"]
    last_message = messages[-1].content if messages else ""
    
    # 判断是否是用户的第一条消息
    is_first_message = len([m for m in messages if isinstance(m, HumanMessage)]) == 1
    
    if is_first_message:
        # 第一次：分析用户问题
        print("   分析用户问题类型...")
        
        # 关键词匹配（实际应该用LLM智能判断）
        tech_keywords = ["错误", "bug", "崩溃", "error", "系统", "服务器", "API"]
        sales_keywords = ["价格", "购买", "产品", "套餐", "订阅", "优惠"]
        billing_keywords = ["发票", "支付", "退款", "账单", "费用"]
        
        if any(keyword in last_message for keyword in tech_keywords):
            next_agent = "tech_support"
            print("   → 路由到：技术支持")
        elif any(keyword in last_message for keyword in sales_keywords):
            next_agent = "sales"
            print("   → 路由到：销售顾问")
        elif any(keyword in last_message for keyword in billing_keywords):
            next_agent = "billing"
            print("   → 路由到：账单专员")
        else:
            # 默认销售
            next_agent = "sales"
            print("   → 路由到：销售顾问（默认）")
    
    else:
        # 任务完成，结束
        next_agent = "FINISH"
        print("   → 任务完成")
    
    return {"next": next_agent}

# ============================================
# 第六步：构建图
# ============================================

# 定义路由函数
def route_after_supervisor(state: SupervisorState) -> Literal["tech_support", "sales", "billing", "__end__"]:
    """根据supervisor的决定路由"""
    next_agent = state["next"]
    
    if next_agent == "FINISH":
        return "__end__"
    return next_agent

# 创建图
workflow = StateGraph(SupervisorState)

# 添加所有节点
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("tech_support", tech_agent_node)
workflow.add_node("sales", sales_agent_node)
workflow.add_node("billing", billing_agent_node)

# 流程设计：
# START → supervisor → (tech/sales/billing) → END
workflow.add_edge(START, "supervisor")

workflow.add_conditional_edges(
    "supervisor",
    route_after_supervisor,
    {
        "tech_support": "tech_support",
        "sales": "sales",
        "billing": "billing",
        "__end__": END
    }
)

# 每个Agent执行完后直接结束（简单版本）
# 复杂版本可以再回到supervisor
workflow.add_edge("tech_support", END)
workflow.add_edge("sales", END)
workflow.add_edge("billing", END)

# 编译
app = workflow.compile()

# ============================================
# 第七步：可视化
# ============================================
print("\n📊 系统架构：")
print("""
           用户问题
              ↓
        [Supervisor]  ← 智能路由
         /    |    \\
        ↓     ↓     ↓
   [技术支持][销售][账单]
         \\    |    /
              ↓
           用户回复
""")

# ============================================
# 第八步：测试系统
# ============================================

test_cases = [
    "我遇到500错误，系统无法访问",
    "我想了解专业版的价格和优惠",
    "我需要查询ORD001的发票",
    "服务器好像有问题，能帮我看看吗？",
    "基础版和专业版有什么区别？多少钱？",
]

print("\n" + "="*70)
print("开始测试多Agent系统")
print("="*70)

for i, query in enumerate(test_cases, 1):
    print(f"\n{'='*70}")
    print(f"测试案例 {i}")
    print("="*70)
    print(f"👤 用户: {query}")
    
    result = app.invoke({
        "messages": [HumanMessage(content=query)],
        "next": ""
    })
    
    # 打印Agent回复
    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            print(f"\n{msg.content}")
    
    print(f"\n✅ 最终状态: {result['next']}")

print("\n" + "="*70)
print("测试完成！")
print("="*70)