# ============ 案例5：完整聊天机器人 ============
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Annotated
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph.message import add_messages

print("\n" + "=" * 50)
print("案例5: 完整聊天机器人")
print("=" * 50)


# 使用add_messages reducer管理对话历史
class ChatBotState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    current_topic: str
    user_emotion: str


def detect_emotion(state: ChatBotState):
    """情绪检测节点"""
    last_message = state["messages"][-1].content.lower()

    if any(word in last_message for word in ["难过", "伤心", "糟糕"]):
        emotion = "sad"
    elif any(word in last_message for word in ["开心", "高兴", "棒"]):
        emotion = "happy"
    else:
        emotion = "neutral"

    print(f"检测到情绪: {emotion}")
    return {"user_emotion": emotion}


def detect_topic(state: ChatBotState):
    """话题检测节点"""
    last_message = state["messages"][-1].content.lower()

    if any(word in last_message for word in ["天气", "气温"]):
        topic = "weather"
    elif any(word in last_message for word in ["新闻", "资讯"]):
        topic = "news"
    else:
        topic = "chat"

    print(f"检测到话题: {topic}")
    return {"current_topic": topic}


def generate_response(state: ChatBotState):
    """生成回复节点"""
    emotion = state["user_emotion"]
    topic = state["current_topic"]

    # 根据情绪和话题生成不同的回复
    if emotion == "sad":
        if topic == "weather":
            response = "天气不好可能会影响心情。要不要聊点开心的事？☀️"
        else:
            response = "我能感觉到你的情绪。有什么我可以帮助的吗？🤗"
    elif emotion == "happy":
        if topic == "weather":
            response = "是啊！好天气让人心情愉悦！😊"
        else:
            response = "太好了！很高兴看到你开心！🎉"
    else:
        if topic == "weather":
            response = "今天天气不错，温度适宜。"
        elif topic == "news":
            response = "最近有很多有趣的科技新闻。"
        else:
            response = "我在这里，有什么可以帮你的吗？"

    print(f"生成回复: {response}")

    # 使用add_messages，新消息会自动添加到列表
    return {"messages": [AIMessage(content=response)]}


# 构建图
workflow = StateGraph(ChatBotState)

workflow.add_node("emotion", detect_emotion)
workflow.add_node("topic", detect_topic)
workflow.add_node("respond", generate_response)

# 先检测情绪和话题，再生成回复
workflow.add_edge(START, "emotion")
workflow.add_edge("emotion", "topic")
workflow.add_edge("topic", "respond")
workflow.add_edge("respond", END)

app = workflow.compile()

# 测试多轮对话
test_conversations = [
    "今天天气真好！",
    "但是我有点难过",
    "有什么新闻吗？"
]

# 初始状态
state = {
    "messages": [],
    "current_topic": "",
    "user_emotion": ""
}

print("\n开始对话：")
print("=" * 40)

for user_input in test_conversations:
    print(f"\n👤 用户: {user_input}")

    # 添加用户消息并运行
    state["messages"].append(HumanMessage(content=user_input))
    result = app.invoke(state)

    # 更新状态（保留对话历史）
    state = result

    # 获取AI的回复
    ai_response = result["messages"][-1].content
    print(f"🤖 助手: {ai_response}")

print("\n" + "=" * 40)
print(f"总对话轮数: {len(state['messages']) // 2}")