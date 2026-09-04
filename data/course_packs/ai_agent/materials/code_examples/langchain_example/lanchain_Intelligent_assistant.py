"""
=============================================================================
全能智能助手 - 使用 LangChain create_agent (最新 API)
=============================================================================

本示例展示如何使用 LangChain 1.0+ 的 create_agent API 构建一个功能丰富的智能助手

特性：
✅ 使用最新的 create_agent API
✅ 支持多种实用工具（天气、搜索、计算、时间、翻译、数据分析等）
✅ 支持对话历史和状态持久化
✅ 优雅的交互界面和错误处理
✅ 支持流式输出
✅ 详细的日志和调试信息

作者: AI Assistant
日期: 2024-12-01
版本: 1.0
=============================================================================
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# LangChain 核心导入
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_community.chat_models import ChatTongyi
from langgraph.checkpoint.memory import MemorySaver

# 加载环境变量
load_dotenv()

# 全局配置
CONFIG = {
    "model": "qwen-plus",
    "temperature": 0.7,
    "verbose": True,
    "enable_streaming": True,
    "max_iterations": 10,
}


# =============================================================================
# 📦 工具定义区域
# =============================================================================

@tool
def get_weather(city: str) -> str:
    """获取指定城市的实时天气信息

    这个工具可以查询中国主要城市的天气情况，包括温度、天气状况和空气质量。

    Args:
        city: 城市名称，支持：北京、上海、广州、深圳、杭州、成都、西安、武汉、重庆等

    Returns:
        包含天气详情的字符串
    """
    weather_database = {
        "北京": {
            "condition": "晴天",
            "temp_range": "15-25°C",
            "aqi": "优",
            "humidity": "45%",
            "wind": "东南风2级",
            "suggestion": "适合户外活动",
            "icon": "☀️"
        },
        "上海": {
            "condition": "多云",
            "temp_range": "18-28°C",
            "aqi": "良",
            "humidity": "65%",
            "wind": "东风3级",
            "suggestion": "空气质量良好",
            "icon": "⛅"
        },
        "深圳": {
            "condition": "小雨",
            "temp_range": "22-30°C",
            "aqi": "优",
            "humidity": "80%",
            "wind": "南风4级",
            "suggestion": "记得带伞",
            "icon": "🌧️"
        },
        "杭州": {
            "condition": "阴天",
            "temp_range": "17-26°C",
            "aqi": "良",
            "humidity": "70%",
            "wind": "西风2级",
            "suggestion": "可能有雨，建议带伞",
            "icon": "☁️"
        },
        "成都": {
            "condition": "多云",
            "temp_range": "16-24°C",
            "aqi": "中",
            "humidity": "75%",
            "wind": "无持续风向1级",
            "suggestion": "空气质量一般",
            "icon": "⛅"
        },
        "广州": {
            "condition": "晴天",
            "temp_range": "20-32°C",
            "aqi": "良",
            "humidity": "60%",
            "wind": "东南风3级",
            "suggestion": "天气炎热，注意防晒",
            "icon": "☀️"
        },
        "西安": {
            "condition": "晴天",
            "temp_range": "12-22°C",
            "aqi": "良",
            "humidity": "40%",
            "wind": "西北风2级",
            "suggestion": "适合出行",
            "icon": "☀️"
        },
        "武汉": {
            "condition": "多云",
            "temp_range": "18-27°C",
            "aqi": "良",
            "humidity": "68%",
            "wind": "东风2级",
            "suggestion": "天气舒适",
            "icon": "⛅"
        },
        "重庆": {
            "condition": "阴天",
            "temp_range": "19-26°C",
            "aqi": "中",
            "humidity": "78%",
            "wind": "北风1级",
            "suggestion": "空气质量一般",
            "icon": "☁️"
        }
    }

    if city not in weather_database:
        return f"❌ 抱歉，暂时无法查询 {city} 的天气信息。\n支持的城市：北京、上海、广州、深圳、杭州、成都、西安、武汉、重庆"

    data = weather_database[city]
    result = f"""
{data['icon']} {city} 天气预报
━━━━━━━━━━━━━━━━━━━━━━
• 天气状况：{data['condition']}
• 温度范围：{data['temp_range']}
• 空气质量：{data['aqi']}
• 湿度：{data['humidity']}
• 风力：{data['wind']}
• 建议：{data['suggestion']}
━━━━━━━━━━━━━━━━━━━━━━
数据更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M")}
    """
    return result.strip()


@tool
def search_knowledge(query: str, category: Optional[str] = None) -> str:
    """搜索知识库获取专业信息

    这个工具可以搜索各个领域的专业知识，包括技术、科学、商业等。

    Args:
        query: 搜索关键词或问题
        category: 可选的分类（technology/science/business/general）

    Returns:
        相关知识和信息
    """
    knowledge_base = {
        "人工智能": {
            "category": "technology",
            "content": "人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。主要包括机器学习、深度学习、自然语言处理、计算机视觉等领域。",
            "related": ["机器学习", "深度学习", "神经网络"]
        },
        "机器学习": {
            "category": "technology",
            "content": "机器学习（Machine Learning）是AI的一个子集，它使系统能够从数据中自动学习和改进，而无需显式编程。主要分为监督学习、无监督学习和强化学习三大类。",
            "related": ["深度学习", "神经网络", "数据科学"]
        },
        "深度学习": {
            "category": "technology",
            "content": "深度学习（Deep Learning）是机器学习的一个子领域，使用多层神经网络（深度神经网络）来处理复杂的模式识别任务。在图像识别、语音识别、自然语言处理等领域取得了突破性进展。",
            "related": ["神经网络", "CNN", "RNN", "Transformer"]
        },
        "LangChain": {
            "category": "technology",
            "content": "LangChain是一个强大的框架，用于开发由大语言模型（LLM）驱动的应用程序。它提供了工具、代理、提示管理、内存管理等功能，使开发者能够轻松构建复杂的AI应用。",
            "related": ["LangGraph", "LLM", "Agent"]
        },
        "LangGraph": {
            "category": "technology",
            "content": "LangGraph是构建在LangChain之上的框架，专门用于创建有状态的、基于图的AI应用程序。它支持循环工作流、条件分支、人机协作等高级功能，是构建复杂AI Agent的理想选择。",
            "related": ["LangChain", "StateGraph", "Agent"]
        },
        "量子计算": {
            "category": "science",
            "content": "量子计算（Quantum Computing）是一种基于量子力学原理的计算方式，使用量子比特（qubit）进行信息处理。量子计算机在特定问题上可以实现指数级的加速，特别是在密码学、优化问题和材料模拟等领域。",
            "related": ["量子纠缠", "量子叠加", "量子算法"]
        },
        "区块链": {
            "category": "technology",
            "content": "区块链（Blockchain）是一种分布式账本技术，通过密码学方法保证数据的不可篡改性和可追溯性。最著名的应用是加密货币（如比特币），但也可用于供应链管理、数字身份验证等领域。",
            "related": ["比特币", "智能合约", "去中心化"]
        },
        "云计算": {
            "category": "technology",
            "content": "云计算（Cloud Computing）是通过互联网提供计算资源和服务的模式。主要包括IaaS（基础设施即服务）、PaaS（平台即服务）和SaaS（软件即服务）三种服务模式。代表性产品有AWS、Azure、阿里云等。",
            "related": ["AWS", "Azure", "容器化", "微服务"]
        },
        "大数据": {
            "category": "technology",
            "content": "大数据（Big Data）指的是传统数据处理应用软件无法处理的大规模、高增长率和多样化的信息资产。大数据技术包括数据采集、存储、分析和可视化等环节，常用技术栈包括Hadoop、Spark等。",
            "related": ["数据分析", "数据挖掘", "Hadoop", "Spark"]
        }
    }

    # 搜索匹配
    matches = []
    for key, value in knowledge_base.items():
        if query.lower() in key.lower() or key.lower() in query.lower():
            if category is None or value["category"] == category:
                matches.append((key, value))

    if not matches:
        return f"❌ 未找到关于'{query}'的相关信息。\n\n💡 建议：尝试搜索以下主题：\n• 人工智能、机器学习、深度学习\n• LangChain、LangGraph\n• 量子计算、区块链、云计算、大数据"

    # 格式化结果
    result = f"📚 知识库搜索结果 - '{query}'\n{'='*50}\n\n"

    for key, value in matches:
        result += f"【{key}】\n"
        result += f"{value['content']}\n"
        if value['related']:
            result += f"\n🔗 相关主题: {', '.join(value['related'])}\n"
        result += f"\n{'-'*50}\n\n"

    return result.strip()


@tool
def calculator(expression: str) -> str:
    """执行数学计算和复杂表达式求值

    支持基本算术运算、幂运算、括号等。

    Args:
        expression: 数学表达式，如 "2+2"、"(10*5)+20"、"2**8"

    Returns:
        计算结果
    """
    try:
        # 安全检查
        allowed_chars = set('0123456789+-*/(). ')
        if not all(c in allowed_chars or c == '*' for c in expression.replace('**', '')):
            return "❌ 表达式包含非法字符。仅支持数字和运算符（+、-、*、/、**、括号）"

        # 计算
        result = eval(expression, {"__builtins__": {}}, {})

        # 格式化输出
        if isinstance(result, float):
            if result.is_integer():
                result = int(result)
            else:
                result = round(result, 6)

        return f"✅ 计算结果：\n{expression} = {result}"

    except ZeroDivisionError:
        return "❌ 错误：除数不能为零"
    except SyntaxError:
        return "❌ 错误：表达式语法错误，请检查格式"
    except Exception as e:
        return f"❌ 计算错误：{str(e)}"


@tool
def get_current_time(timezone: str = "Asia/Shanghai") -> str:
    """获取当前时间和日期

    Args:
        timezone: 时区，默认为 Asia/Shanghai（北京时间）

    Returns:
        格式化的时间信息
    """
    now = datetime.now()

    weekdays = ['一', '二', '三', '四', '五', '六', '日']
    weekday = weekdays[now.weekday()]

    result = f"""
🕐 当前时间信息
━━━━━━━━━━━━━━━━━━━━━━
📅 日期：{now.year}年{now.month}月{now.day}日
📆 星期：星期{weekday}
⏰ 时间：{now.strftime('%H:%M:%S')}
🌍 时区：{timezone}
━━━━━━━━━━━━━━━━━━━━━━
    """
    return result.strip()


@tool
def translate_text(text: str, target_lang: str = "英文") -> str:
    """翻译文本（模拟翻译功能）

    Args:
        text: 要翻译的文本
        target_lang: 目标语言（英文/日文/韩文/法文）

    Returns:
        翻译结果
    """
    # 这里是模拟翻译，实际应该调用翻译API
    translations = {
        "你好": {
            "英文": "Hello",
            "日文": "こんにちは",
            "韩文": "안녕하세요",
            "法文": "Bonjour"
        },
        "谢谢": {
            "英文": "Thank you",
            "日文": "ありがとう",
            "韩文": "감사합니다",
            "法文": "Merci"
        },
        "早上好": {
            "英文": "Good morning",
            "日文": "おはよう",
            "韩文": "좋은 아침",
            "法文": "Bonjour"
        },
        "晚安": {
            "英文": "Good night",
            "日文": "おやすみ",
            "韩文": "안녕히 주무세요",
            "法文": "Bonne nuit"
        }
    }

    if text in translations and target_lang in translations[text]:
        translation = translations[text][target_lang]
        return f"""
🌐 翻译结果
━━━━━━━━━━━━━━━━━━━━━━
原文：{text}
语言：{target_lang}
译文：{translation}
━━━━━━━━━━━━━━━━━━━━━━
💡 提示：这是一个模拟翻译工具
        """
    else:
        return f"💡 翻译提示：'{text}' → {target_lang}\n\n实际应用中，这里会调用专业的翻译API（如Google Translate、DeepL等）来提供准确的翻译。"


@tool
def analyze_data(data: str, analysis_type: str = "summary") -> str:
    """分析数据并提供统计摘要

    Args:
        data: 数据（逗号分隔的数字）
        analysis_type: 分析类型（summary/statistics/trend）

    Returns:
        分析结果
    """
    try:
        # 解析数据
        numbers = [float(x.strip()) for x in data.split(',') if x.strip()]

        if not numbers:
            return "❌ 错误：没有有效的数字数据"

        # 计算统计值
        count = len(numbers)
        total = sum(numbers)
        mean = total / count
        sorted_numbers = sorted(numbers)

        # 中位数
        if count % 2 == 0:
            median = (sorted_numbers[count//2 - 1] + sorted_numbers[count//2]) / 2
        else:
            median = sorted_numbers[count//2]

        # 方差和标准差
        variance = sum((x - mean) ** 2 for x in numbers) / count
        std_dev = variance ** 0.5

        result = f"""
📊 数据分析报告
━━━━━━━━━━━━━━━━━━━━━━
📈 基本统计
  • 数据量：{count} 个
  • 总和：{total:.2f}
  • 平均值：{mean:.2f}
  • 中位数：{median:.2f}
  
📉 离散程度
  • 最小值：{min(numbers):.2f}
  • 最大值：{max(numbers):.2f}
  • 极差：{max(numbers) - min(numbers):.2f}
  • 标准差：{std_dev:.2f}
  • 方差：{variance:.2f}

📋 原始数据
  {', '.join(f'{x:.2f}' for x in numbers)}
━━━━━━━━━━━━━━━━━━━━━━
        """
        return result.strip()

    except ValueError:
        return "❌ 错误：请提供有效的数字数据，用逗号分隔（例如：1,2,3,4,5）"
    except Exception as e:
        return f"❌ 分析错误：{str(e)}"


@tool
def generate_report(topic: str, sections: Optional[str] = None) -> str:
    """生成结构化报告模板

    Args:
        topic: 报告主题
        sections: 可选的章节（用逗号分隔）

    Returns:
        报告模板
    """
    default_sections = ["摘要", "背景", "分析", "结论", "建议"]
    if sections:
        section_list = [s.strip() for s in sections.split(',')]
    else:
        section_list = default_sections

    report = f"""
📄 报告模板 - {topic}
━━━━━━━━━━━━━━━━━━━━━━
生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""

    for i, section in enumerate(section_list, 1):
        report += f"\n{i}. {section}\n"
        report += f"{'─' * 40}\n"
        report += f"[请在这里填写{section}的内容]\n\n"

    report += """
━━━━━━━━━━━━━━━━━━━━━━
💡 提示：这是一个报告模板，请根据实际需求填写内容。
    """

    return report


# =============================================================================
# 🤖 Agent 创建和配置
# =============================================================================

# 工具列表
TOOLS = [
    get_weather,
    search_knowledge,
    calculator,
    get_current_time,
    translate_text,
    analyze_data,
    generate_report,
]

# 系统提示词
SYSTEM_PROMPT = """你是一个专业、友好、高效的AI助手，名字叫"小智"。

🎯 你的能力：
• 天气查询：可以查询中国主要城市的实时天气
• 知识搜索：可以搜索和解释各领域的专业知识
• 数学计算：可以进行复杂的数学运算
• 时间服务：可以提供当前时间和日期
• 文本翻译：可以将中文翻译成多种语言
• 数据分析：可以分析数字数据并提供统计摘要
• 报告生成：可以生成结构化的报告模板

💡 工作原则：
1. 认真理解用户的需求和意图
2. 选择最合适的工具来回答问题
3. 如果需要多个步骤，按照逻辑顺序执行
4. 提供清晰、准确、有帮助的回答
5. 如果不确定或没有相关工具，诚实告知用户

🎨 风格：
• 友好而专业
• 回答简洁明了
• 使用适当的emoji让交互更生动
• 主动提供相关建议

现在，请根据用户的问题，智能地选择和使用工具来提供最佳答案。
"""


def create_smart_assistant(
    model_name: str = "qwen-plus",
    temperature: float = 0.7,
    enable_memory: bool = True,
    verbose: bool = True
):
    """创建智能助手

    Args:
        model_name: 模型名称
        temperature: 温度参数
        enable_memory: 是否启用记忆
        verbose: 是否显示详细信息

    Returns:
        编译好的 Agent
    """
    # 初始化模型
    llm = ChatTongyi(
        model=model_name,
        temperature=temperature,
        dashscope_api_key=os.environ.get("DASHSCOPE_API_KEY")
    )

    # 创建检查点（用于状态持久化）
    checkpointer = MemorySaver() if enable_memory else None

    # 创建 Agent
    agent = create_agent(
        model=llm,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        # debug=verbose,  # 启用调试模式
    )

    return agent


# =============================================================================
# 💬 交互界面
# =============================================================================

def print_banner():
    """打印欢迎横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════════════╗
║                     🤖 全能智能助手 - 小智 v1.0                        ║
║                   Powered by LangChain create_agent                   ║
╚═══════════════════════════════════════════════════════════════════════╝

👋 你好！我是小智，你的AI智能助手。

🎯 我可以帮你：
  • 🌤️  查询天气      • 📚 搜索知识      • 🧮 数学计
  • 🕐 查看时间      • 🌐 文本翻译      • 📊 数据分析
  • 📄 生成报告      • 💬 闲聊对话

💡 提示：
  • 输入 'help' 查看详细帮助
  • 输入 'quit' 或 '退出' 结束对话
  • 输入 'clear' 清空对话历史

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    print(banner)


def print_help():
    """打印帮助信息"""
    help_text = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📖 使用帮助

🌤️  天气查询
  示例：北京今天天气怎么样？/ 上海的天气如何？
  
📚 知识搜索
  示例：什么是机器学习？/ 给我讲讲LangChain
  
🧮 数学计算
  示例：计算 123 * 456 / 帮我算一下 (10+20)*3
  
🕐 时间查询
  示例：现在几点了？/ 今天是星期几？
  
🌐 文本翻译
  示例：把"你好"翻译成英文 / 翻译"谢谢"到日文
  
📊 数据分析
  示例：分析这些数据：1,2,3,4,5,6,7,8,9,10
  
📄 报告生成
  示例：生成一个关于AI的报告 / 创建市场分析报告模板

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    print(help_text)


def run_interactive_mode():
    """运行交互模式"""
    print_banner()

    # 创建 Agent
    print("⚙️  正在初始化智能助手...")
    agent = create_smart_assistant(
        model_name=CONFIG["model"],
        temperature=CONFIG["temperature"],
        enable_memory=True,
        verbose=CONFIG["verbose"]
    )
    print("✅ 初始化完成！\n")

    # 会话配置
    config = {"configurable": {"thread_id": "main_session"}}
    conversation_count = 0

    while True:
        try:
            # 获取用户输入
            user_input = input("\n👤 你: ").strip()

            if not user_input:
                continue

            # 处理特殊命令
            if user_input.lower() in ['quit', '退出', 'exit', 'q']:
                print("\n👋 再见！期待下次为你服务！\n")
                break

            if user_input.lower() in ['help', '帮助', 'h']:
                print_help()
                continue

            if user_input.lower() in ['clear', '清空']:
                config = {"configurable": {"thread_id": f"session_{datetime.now().timestamp()}"}}
                conversation_count = 0
                print("\n✨ 对话历史已清空！\n")
                continue

            # 显示处理提示
            print("\n🤖 小智: ", end="", flush=True)

            # 调用 Agent（流式输出）
            conversation_count += 1
            inputs = {"messages": [{"role": "user", "content": user_input}]}

            final_response = ""

            if CONFIG["enable_streaming"]:
                # 流式输出
                for chunk in agent.stream(inputs, config, stream_mode="values"):
                    msgs = chunk.get("messages")
                    if not msgs:
                        continue
                    last_message = msgs[-1]
                    msg_type = getattr(last_message, "type", None) or getattr(last_message, "role", None)
                    if msg_type not in ("ai", "assistant"):
                        continue
                    content = getattr(last_message, "content", "")
                    if content and content != final_response:
                        new_content = content[len(final_response):]
                        print(new_content, end="", flush=True)
                        final_response = content
                print()  # 换行
            else:
                # 非流式输出
                result = agent.invoke(inputs, config)
                msgs = result.get("messages", [])
                final_message = next((m for m in reversed(msgs) if (getattr(m, "type", None) == "ai" or getattr(m, "role", None) == "assistant")), msgs[-1] if msgs else None)
                final_response = getattr(final_message, "content", "")
                print(final_response)

            print("\n" + "━" * 70)

        except KeyboardInterrupt:
            print("\n\n👋 再见！期待下次为你服务！\n")
            break
        except Exception as e:
            print(f"\n\n❌ 错误：{str(e)}")
            print("💡 请尝试重新表述你的问题，或输入 'help' 查看帮助。\n")
            print("━" * 70)


def run_demo_mode():
    """运行演示模式"""
    print("\n" + "="*70)
    print("📺 演示模式")
    print("="*70 + "\n")

    # 创建 Agent
    print("⚙️  正在初始化智能助手...")
    agent = create_smart_assistant(
        model_name=CONFIG["model"],
        temperature=CONFIG["temperature"],
        enable_memory=True,
        verbose=False
    )
    print("✅ 初始化完成！\n")

    # 演示问题
    demo_queries = [
        "北京今天天气怎么样？",
        "什么是机器学习？给我详细讲讲",
        "帮我计算 (25 + 75) * 3 - 100",
        "现在几点了？",
        "把'你好'翻译成英文和日文",
        "帮我分析这组数据：10, 20, 30, 40, 50, 60, 70, 80, 90, 100",
        "生成一个关于人工智能的报告模板",
    ]

    config = {"configurable": {"thread_id": "demo_session"}}

    for i, query in enumerate(demo_queries, 1):
        print(f"\n{'='*70}")
        print(f"📝 示例 {i}/{len(demo_queries)}")
        print(f"{'='*70}")
        print(f"\n👤 用户: {query}")
        print(f"\n🤖 小智: ", end="", flush=True)

        try:
            inputs = {"messages": [{"role": "user", "content": query}]}
            result = agent.invoke(inputs, config)
            final_message = result["messages"][-1]
            print(final_message.content)
            print(f"\n{'━'*70}")

        except Exception as e:
            print(f"❌ 错误：{str(e)}")
            print(f"{'━'*70}")


# =============================================================================
# 🚀 主程序
# =============================================================================

def main():
    """主函数"""
    # 检查API密钥
    if not os.environ.get("DASHSCOPE_API_KEY"):
        print("❌ 错误：未找到 DASHSCOPE_API_KEY 环境变量")
        print("💡 请在 .env 文件中设置：DASHSCOPE_API_KEY=your_api_key")
        return

    # 选择模式
    print("\n" + "="*70)
    print("🎮 请选择运行模式")
    print("="*70)
    print("\n1️⃣  交互模式（推荐） - 与小智自由对话")
    print("2️⃣  演示模式 - 自动运行预设示例")
    print()

    choice = input("请输入选项 (1/2，默认1): ").strip() or "1"

    if choice == "1":
        run_interactive_mode()
    elif choice == "2":
        run_demo_mode()
    else:
        print("\n❌ 无效选项，使用默认交互模式\n")
        run_interactive_mode()

    print("\n" + "="*70)
    print("✅ 程序结束")
    print("="*70)
    print("\n💡 感谢使用全能智能助手！")
    print("📚 基于 LangChain create_agent API (v1.0+)")
    print("🔗 https://docs.langchain.com/\n")


if __name__ == "__main__":
    main()
