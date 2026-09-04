"""
@Author  : yo-pai
@GitHub  : https://github.com/yo-pai
带记忆的智能对话机器人 🤖
"""
# ============================================
# 案例1：带记忆的智能对话机器人
# ============================================

import os
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.llms import Tongyi

print("=" * 60)
print("案例1: 带记忆的智能对话机器人")
print("=" * 60)

# 1. 设置API Key
if not os.environ.get("DASHSCOPE_API_KEY"):
    raise RuntimeError("请先设置环境变量 DASHSCOPE_API_KEY")

# 2. 初始化Qwen模型
llm = Tongyi(
    model="qwen-plus",  # 可选: qwen-turbo, qwen-plus, qwen-max
    temperature=0.7,  # 控制创造性 (0-1)
    top_p=0.8,  # 控制多样性
    streaming=True,  # 流式输出
)


# 3. 定义状态（使用MessagesState自动管理消息历史）
class ChatState(MessagesState):
    """继承MessagesState，自动包含messages字段"""
    user_name: str  # 额外字段：用户名
    conversation_count: int  # 对话轮数


# 4. 定义聊天节点
def chatbot_node(state: ChatState):
    """调用Qwen模型生成回复"""

    # 构建系统提示词
    system_prompt = f"""你是一个友好、专业的AI助手。
用户名: {state.get('user_name', '未知用户')}
当前是第 {state.get('conversation_count', 0)} 轮对话。

请用中文回答，保持礼貌和专业。"""

    # 构建完整消息列表（包含历史）
    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    # 调用Qwen
    response = llm.invoke(messages)
    # print(response)

    # 更新对话轮数
    new_count = state.get("conversation_count", 0) + 1

    return {
        "messages": [AIMessage(content=response)],
        "conversation_count": new_count
    }


# 5. 构建图
workflow = StateGraph(ChatState)
workflow.add_node("chatbot", chatbot_node)
workflow.add_edge(START, "chatbot")
workflow.add_edge("chatbot", END)

# 6. 编译
app = workflow.compile()

# 7. 测试对话（多轮）
print("\n开始多轮对话测试：\n")

# 初始化状态
state = {
    "messages": [],
    "user_name": "小明",
    "conversation_count": 0
}

# 第一轮对话
print("👤 用户: 你好，我是小明")
state["messages"].append(HumanMessage(content="你好，我是小明"))
result = app.invoke(state)
state = result
print(f"🤖 助手: {result['messages'][-1].content}\n")

# 第二轮对话
print("👤 用户: 我刚才说我叫什么？")
state["messages"].append(HumanMessage(content="我刚才说我叫什么？"))
result = app.invoke(state)
state = result
print(f"🤖 助手: {result['messages'][-1].content}\n")

# 第三轮对话
print("👤 用户: 帮我推荐一本关于Python的书")
state["messages"].append(HumanMessage(content="帮我推荐一本关于Python的书"))
result = app.invoke(state)
state = result
print(f"🤖 助手: {result['messages'][-1].content}\n")

print(f"总对话轮数: {result['conversation_count']}")