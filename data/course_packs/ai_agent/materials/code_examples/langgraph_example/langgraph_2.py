# ============================================
# 案例2：带工具调用的智能助手
# ============================================

import os
from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_community.chat_models import QianfanChatEndpoint
import json

print("\n" + "="*60)
print("案例2: 带工具调用的智能助手")
print("="*60)

# 1. 定义工具
@tool
def search_web(query: str) -> str:
    """搜索网络信息

    Args:
        query: 搜索关键词
    """
    # 模拟搜索（实际应该调用真实搜索API）
    results = {
        "Python": "Python是一种广泛使用的高级编程语言...",
        "北京天气": "北京今天晴，温度15-25度",
        "LangGraph": "LangGraph是用于构建状态化AI应用的框架..."
    }

    for key in results:
        if key.lower() in query.lower():
            return f"搜索结果：{results[key]}"

    return f"搜索 '{query}' 的结果：暂无相关信息"

@tool
def calculator(expression: str) -> str:
    """计算数学表达式

    Args:
        expression: 数学表达式，如 "2+2" 或 "3*4"
    """
    try:
        result = eval(expression)
        return f"计算结果: {expression} = {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"

@tool
def get_weather(city: str) -> str:
    """查询城市天气

    Args:
        city: 城市名称
    """
    # 模拟天气数据
    weather_data = {
        "北京": "晴天，15-25度",
        "上海": "多云，18-28度",
        "深圳": "小雨，20-30度"
    }

    return weather_data.get(city, f"{city}的天气信息暂不可用")

# 2. 工具列表
tools = [search_web, calculator, get_weather]
tool_names = [tool.name for tool in tools]

# 3. 定义状态
class AgentState(MessagesState):
    """智能助手状态"""
    pass

# 4. 定义节点

def agent_node(state: AgentState):
    """智能体决策节点：决定是否需要调用工具"""

    # 获取最后一条用户消息
    last_message = state["messages"][-1].content

    # 简单的意图识别（实际应该用LLM）
    response = None
    tool_to_use = None

    if any(word in last_message for word in ["搜索", "查询", "找"]):
        # 需要搜索
        query = last_message.replace("搜索", "").replace("查询", "").strip()
        tool_to_use = "search_web"
        args = {"query": query}

    elif any(word in last_message for word in ["计算", "等于", "+", "-", "*", "/"]):
        # 需要计算
        tool_to_use = "calculator"
        # 提取数学表达式
        import re
        expr = re.findall(r'[\d\+\-\*/\(\)\.]+', last_message)
        args = {"expression": expr[0] if expr else "0"}

    elif "天气" in last_message:
        # 需要查天气
        tool_to_use = "get_weather"
        # 提取城市名
        cities = ["北京", "上海", "深圳"]
        city = next((c for c in cities if c in last_message), "北京")
        args = {"city": city}

    else:
        # 直接回答
        response = AIMessage(content="你好！我可以帮你搜索信息、计算数学题或查询天气。")
        return {"messages": [response]}

    # 返回工具调用决策
    if tool_to_use:
        print(f"🔧 决定调用工具: {tool_to_use}")
        print(f"   参数: {args}")

        # 创建工具调用消息
        tool_call_message = AIMessage(
            content="",
            additional_kwargs={
                "tool_calls": [{
                    "name": tool_to_use,
                    "args": args
                }]
            }
        )
        return {"messages": [tool_call_message]}

def tool_execution_node(state: AgentState):
    """工具执行节点"""

    last_message = state["messages"][-1]
    tool_calls = last_message.additional_kwargs.get("tool_calls", [])

    if not tool_calls:
        return {"messages": []}

    # 执行工具
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        # 找到对应的工具并执行
        tool_func = next((t for t in tools if t.name == tool_name), None)
        if tool_func:
            result = tool_func.invoke(tool_args)
            print(f"✅ 工具执行结果: {result}")
            results.append(ToolMessage(content=result, tool_call_id=tool_name))

    return {"messages": results}

def response_node(state: AgentState):
    """生成最终回复"""

    # 获取工具结果
    tool_results = [msg for msg in state["messages"] if isinstance(msg, ToolMessage)]

    if tool_results:
        # 基于工具结果生成回复
        result_text = tool_results[-1].content
        response = AIMessage(content=f"根据查询结果：\n{result_text}")
    else:
        response = AIMessage(content="已为您处理完成。")

    return {"messages": [response]}

# 5. 路由函数
def should_use_tool(state: AgentState) -> Literal["use_tool", "respond"]:
    """判断是否需要使用工具"""
    last_message = state["messages"][-1]

    if hasattr(last_message, "additional_kwargs"):
        if last_message.additional_kwargs.get("tool_calls"):
            return "use_tool"

    return "respond"

# 6. 构建图
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_execution_node)
workflow.add_node("respond", response_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_use_tool,
    {
        "use_tool": "tools",
        "respond": END
    }
)
workflow.add_edge("tools", "respond")
workflow.add_edge("respond", END)

app = workflow.compile()

# 7. 测试
test_queries = [
    "帮我搜索 Python",
    "计算 123 + 456",
    "北京的天气怎么样？",
    "你好"
]

for query in test_queries:
    print(f"\n{'='*40}")
    print(f"👤 用户: {query}")
    print("="*40)

    result = app.invoke({
        "messages": [HumanMessage(content=query)]
    })

    print(f"🤖 助手: {result['messages'][-1].content}")