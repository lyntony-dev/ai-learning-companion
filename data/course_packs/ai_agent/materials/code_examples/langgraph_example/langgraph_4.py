# ============================================
# 案例4：流式输出 - 实时打字机效果
# ============================================

import os
import time
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.llms import Tongyi

print("\n" + "=" * 60)
print("案例5: 流式输出 - 实时对话体验")
print("=" * 60)

os.environ["DASHSCOPE_API_KEY"] = ""

# 1. 启用流式输出的模型
llm = Tongyi(
    model="qwen-plus",
    streaming=True,  # 关键：启用流式输出
    temperature=0.7
)


# 2. 定义状态
class StreamState(MessagesState):
    pass


# 3. 流式聊天节点
def streaming_chat_node(state: StreamState):
    """流式生成回复"""

    messages = state["messages"]

    # 使用流式调用
    full_response = ""

    print("🤖 助手: ", end="", flush=True)

    # 流式输出
    for chunk in llm.stream(messages):
        print(chunk, end="", flush=True)
        full_response += chunk
        time.sleep(0.02)  # 模拟打字延迟

    print()  # 换行

    return {"messages": [AIMessage(content=full_response)]}


# 4. 构建图
workflow = StateGraph(StreamState)
workflow.add_node("chat", streaming_chat_node)
workflow.add_edge(START, "chat")
workflow.add_edge("chat", END)

app = workflow.compile()

# 5. 交互式对话
print("\n💬 进入对话模式（输入 'quit' 退出）\n")

conversation_history = []

while True:
    user_input = input("👤 你: ").strip()

    if user_input.lower() in ['quit', 'exit', '退出']:
        print("👋 再见！")
        break

    if not user_input:
        continue

    # 添加用户消息
    conversation_history.append(HumanMessage(content=user_input))

    # 调用图
    result = app.invoke({"messages": conversation_history})

    # 更新历史
    conversation_history = result["messages"]

    print()  # 空行分隔