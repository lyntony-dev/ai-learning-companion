# ============================================
# 案例4: 带记忆和持久化的Agent（V1.0）
# ============================================

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_community.chat_models import ChatTongyi
from langgraph.checkpoint.memory import MemorySaver

print("\n" + "=" * 60)
print("案例4: 带记忆的持久化Agent - V1.0")
print("=" * 60)


# 1. 定义工具
@tool
def save_note(title: str, content: str) -> str:
    """保存笔记

    Args:
        title: 笔记标题
        content: 笔记内容
    """
    # 实际应该保存到数据库
    print(f"💾 保存笔记: {title}")
    return f"✅ 笔记'{title}'已保存"


@tool
def get_time() -> str:
    """获取当前时间"""
    from datetime import datetime
    return f"🕐 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@tool
def translate_text(text: str, target_lang: str) -> str:
    """翻译文本

    Args:
        text: 要翻译的文本
        target_lang: 目标语言 (en/zh/ja/ko)
    """
    # 模拟翻译
    translations = {
        "en": f"Translation to English: {text}",
        "zh": f"翻译成中文: {text}",
        "ja": f"日本語訳: {text}",
        "ko": f"한국어 번역: {text}"
    }
    return translations.get(target_lang, "不支持的语言")


# 2. 创建带记忆的Agent
llm = ChatTongyi(
    model="qwen-plus",
    temperature=0.7,
    dashscope_api_key=""
)

# 创建内存存储
memory = MemorySaver()

agent = create_agent(
    model=llm,
    tools=[save_note, get_time, translate_text],
    system_prompt="你是一个智能助手，可以保存笔记、查询时间和翻译文本。记住用户的对话上下文。",
    checkpointer=memory  # 添加checkpointer启用记忆
)

# 3. 使用线程ID管理会话
config = {"configurable": {"thread_id": "conversation_001"}}

# 4. 多轮对话测试
conversations = [
    "现在几点了？",
    "帮我保存一个笔记，标题是'会议记录'，内容是'今天讨论了项目进展'",
    "我刚才保存的笔记标题是什么？",  # 测试记忆
    "把'Hello World'翻译成中文",
]

print("\n💬 开始多轮对话:")
print("=" * 60)

for i, msg in enumerate(conversations, 1):
    print(f"\n轮次 {i}")
    print(f"👤 用户: {msg}")

    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": msg}]},
            config=config  # 使用相同的thread_id保持对话
        )

        final_message = result["messages"][-1]
        print(f"🤖 助手: {final_message.content}")
    except Exception as e:
        print(f"❌ 错误: {str(e)}")

print("\n" + "=" * 60)
print("💡 说明: Agent通过checkpointer记住了整个对话历史")