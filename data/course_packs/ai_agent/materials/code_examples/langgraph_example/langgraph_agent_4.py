"""
案例1: 单个Agent基础入门 (修正版)
学习目标: 理解Agent的基本概念和创建方法

修正内容:
1. 使用 ChatTongyi 代替 ChatOpenAI
2. 使用 messages_modifier 代替 state_modifier
3. messages_modifier 使用 SystemMessage 对象
"""

import os
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_community.chat_models import ChatTongyi

# 设置API Key
os.environ["DASHSCOPE_API_KEY"] = ""

def create_qwen_model(model_name="qwen-plus", temperature=0.7):
    """创建Qwen模型"""
    return ChatTongyi(
        model=model_name,
        temperature=temperature,
        dashscope_api_key=os.environ["DASHSCOPE_API_KEY"]
    )

# ============================================================================
# 步骤1: 定义工具
# ============================================================================

@tool
def add(a: float, b: float) -> float:
    """将两个数字相加"""
    print(f"🔧 执行加法: {a} + {b}")
    return a + b

@tool
def multiply(a: float, b: float) -> float:
    """将两个数字相乘"""
    print(f"🔧 执行乘法: {a} × {b}")
    return a * b

@tool
def divide(a: float, b: float) -> float:
    """将两个数字相除"""
    if b == 0:
        return "错误: 除数不能为0"
    print(f"🔧 执行除法: {a} ÷ {b}")
    return a / b

# ============================================================================
# 步骤2: 创建Agent
# ============================================================================

print("=" * 80)
print("创建数学计算Agent")
print("=" * 80)

# 创建系统提示词
system_prompt = SystemMessage(content="""你是一个数学计算助手。

你的能力:
- 使用add工具进行加法运算
- 使用multiply工具进行乘法运算  
- 使用divide工具进行除法运算

工作方式:
1. 理解用户的数学问题
2. 将问题分解为基本运算步骤
3. 调用相应的工具执行计算
4. 给出清晰的最终答案

注意: 按正确的运算顺序执行计算。""")

# 创建Agent - 注意参数名称的变化
math_agent = create_react_agent(
    model=create_qwen_model(),
    tools=[add, multiply, divide],
    messages_modifier=system_prompt  # 使用 messages_modifier
)

print("✅ Agent创建成功!\n")

# ============================================================================
# 步骤3: 使用Agent
# ============================================================================

def test_agent(query: str):
    """测试Agent"""
    print("-" * 80)
    print(f"📝 问题: {query}")
    print("-" * 80)

    # 调用Agent
    result = math_agent.invoke({"messages": [HumanMessage(content=query)]})

    # 打印过程
    print("\n执行过程:")
    for i, msg in enumerate(result["messages"], 1):
        msg_type = type(msg).__name__
        content = msg.content if hasattr(msg, 'content') else str(msg)

        if msg_type == "HumanMessage":
            print(f"\n{i}. 👤 用户消息")
        elif msg_type == "AIMessage":
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"\n{i}. 🤖 AI决策: 需要调用工具")
                for tc in msg.tool_calls:
                    print(f"   - 工具: {tc['name']}")
                    print(f"   - 参数: {tc['args']}")
            elif content:
                print(f"\n{i}. 🤖 AI回复: {content}")
        elif msg_type == "ToolMessage":
            print(f"\n{i}. 🔧 工具结果: {content}")

    # 打印最终答案
    print("\n" + "=" * 80)
    print(f"✅ 最终答案: {result['messages'][-1].content}")
    print("=" * 80)
    print()

# 测试案例
print("\n【测试1: 简单加法】")
test_agent("计算 15 + 27")

print("\n【测试2: 多步计算】")
test_agent("计算 (10 + 5) × 3")

print("\n【测试3: 复杂表达式】")
test_agent("先计算 20 × 4,然后将结果除以 8")

# ============================================================================
# 学习要点
# ============================================================================

print("\n" + "=" * 80)
print("📚 学习要点总结")
print("=" * 80)

summary = """
1️⃣  什么是Agent?
   - Agent是具有自主决策能力的智能体
   - 它可以使用工具(Tools)来完成任务
   - LangGraph的Agent基于ReAct模式工作

2️⃣  ReAct模式是什么?
   ReAct = Reasoning + Acting
   - Reasoning: 推理思考下一步做什么
   - Acting: 执行具体的动作(调用工具)
   - 循环这个过程直到任务完成

3️⃣  创建Agent的三要素:
   ✓ Model: 大语言模型(使用ChatTongyi调用Qwen)
   ✓ Tools: Agent可以调用的工具函数
   ✓ Messages Modifier: 系统提示词(使用SystemMessage)

4️⃣  工具(Tool)的定义:
   - 使用 @tool 装饰器
   - 需要清晰的函数名和文档字符串
   - 参数要有类型注解
   - 返回值要明确

5️⃣  Agent的工作流程:
   用户输入 → AI分析 → 决定调用工具 → 工具执行 
   → AI查看结果 → 决定下一步 → ... → 给出答案

6️⃣  调试技巧:
   - 打印消息历史查看完整流程
   - 在工具函数中添加print语句
   - 观察AI的推理过程
   - 调整messages_modifier优化行为

💡 提示:
   - 工具描述越清晰,Agent使用越准确
   - messages_modifier要详细说明Agent的职责
   - 复杂任务需要将Agent分解为多个步骤
   - 测试时从简单案例开始

🔧 重要变化:
   - 模型: 使用 ChatTongyi 而不是 ChatOpenAI
   - 参数: 使用 messages_modifier 而不是 state_modifier
   - 类型: messages_modifier 接受 SystemMessage 对象
"""

print(summary)
print("\n🎉 案例1学习完成!")