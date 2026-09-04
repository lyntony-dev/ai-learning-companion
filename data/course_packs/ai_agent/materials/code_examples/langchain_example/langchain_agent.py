# ============================================
# 案例1：使用V1.0新版create_agent
# ============================================

import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_community.chat_models import ChatTongyi

# 加载环境变量
load_dotenv()

print("=" * 60)
print("案例1: V1.0新版create_agent - Qwen")
print("=" * 60)




# 2. 定义工具
@tool
def get_weather(city: str) -> str:
    """获取指定城市的天气信息

    Args:
        city: 城市名称，如"北京"、"上海"
    """
    weather_db = {
        "北京": "☀️ 晴天，温度15-25度，空气质量优",
        "上海": "☁️ 多云，温度18-28度，有轻度雾霾",
        "深圳": "🌧️ 小雨，温度20-30度，适合室内活动",
        "杭州": "🌥️ 阴天，温度17-26度，建议带伞"
    }
    return weather_db.get(city, f"{city}的天气信息暂不可用")


@tool
def search_knowledge(query: str) -> str:
    """搜索知识库获取信息

    Args:
        query: 搜索关键词
    """
    knowledge_db = {
        "人工智能": "人工智能（AI）是计算机科学的一个分支，它使机器能够执行通常需要人类智能的任务，如学习、推理、问题解决等。",
        "机器学习": "机器学习是AI的一个子集，它使系统能够自动从经验中学习和改进，而无需明确编程。",
        "深度学习": "深度学习是机器学习的一个子领域，使用多层神经网络来处理复杂的模式识别任务。",
        "LangChain": "LangChain是一个用于开发由语言模型驱动的应用程序的框架，提供了工具、代理和内存管理等功能。",
        "LangGraph": "LangGraph是构建在LangChain之上的框架，专门用于创建有状态的、基于图的AI应用程序。"
    }

    for key, value in knowledge_db.items():
        if key in query:
            return f"📚 知识库查询结果：\n{value}"

    return f"未找到关于'{query}'的相关信息"


@tool
def calculator(expression: str) -> str:
    """执行数学计算

    Args:
        expression: 数学表达式，如 "2+2" 或 "10*5"
    """
    try:
        # 安全计算（生产环境需要更严格的验证）
        allowed_chars = set('0123456789+-*/.()')
        if not all(c in allowed_chars or c.isspace() for c in expression):
            return "❌ 表达式包含非法字符"

        result = eval(expression)
        return f"✅ 计算结果: {expression} = {result}"
    except Exception as e:
        return f"❌ 计算错误: {str(e)}"


# 3. 初始化Qwen模型
llm = ChatTongyi(
    model="qwen-plus",
    temperature=0.7,
    dashscope_api_key=os.environ.get("DASHSCOPE_API_KEY")
)

# 4. 创建Agent（V1.0新方式）
agent = create_agent(
    model=llm,
    tools=[get_weather, search_knowledge, calculator],
    system_prompt="你是一个专业的中文助手。仔细分析用户问题，选择合适的工具来回答。"
)

# 5. 测试Agent
test_queries = [
    "北京今天天气怎么样？",
    "给我讲讲什么是机器学习",
    "计算 123 * 456",
]

for query in test_queries:
    print(f"\n{'=' * 50}")
    print(f"👤 用户: {query}")
    print("=" * 50)

    try:
        result = agent.invoke({
            "messages": [{"role": "user", "content": query}]
        })

        # 获取最后的AI消息
        final_message = result["messages"][-1]
        print(f"🤖 助手: {final_message.content}")
    except Exception as e:
        print(f"❌ 错误: {str(e)}")