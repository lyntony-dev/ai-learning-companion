"""
LangChain教程 - 2. Tools（工具）示例

本示例展示如何创建和使用LangChain的工具功能
"""

import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_community.chat_models.tongyi import ChatTongyi
from typing import Optional

# 加载环境变量
load_dotenv()

# 从环境变量获取API密钥
api_key = os.getenv("DASHSCOPE_API_KEY")

# 初始化通义千问模型
llm = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=api_key,
    temperature=0
)

print("=" * 50)
print("示例1: 创建简单的数学工具")
print("=" * 50)


# 使用@tool装饰器创建工具
@tool
def calculator(operation: str, a: float, b: float) -> float:
    """
    执行基本数学运算的计算器工具

    Args:
        operation: 运算类型，可以是 'add'(加), 'subtract'(减), 'multiply'(乘), 'divide'(除)
        a: 第一个数字
        b: 第二个数字

    Returns:
        计算结果
    """
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        if b == 0:
            return "错误：除数不能为0"
        return a / b
    else:
        return "错误：不支持的运算类型"


# 测试工具
result = calculator.invoke({"operation": "multiply", "a": 5, "b": 7})
print(f"5 × 7 = {result}")

print(f"\n工具名称: {calculator.name}")
print(f"工具描述: {calculator.description}")
print(f"工具参数: {calculator.args}")

print("\n" + "=" * 50)
print("示例2: 创建文本处理工具")
print("=" * 50)


@tool
def text_analyzer(text: str) -> dict:
    """
    分析文本的基本统计信息

    Args:
        text: 要分析的文本

    Returns:
        包含统计信息的字典
    """
    words = text.split()
    return {
        "字符数": len(text),
        "单词数": len(words),
        "句子数": text.count('.') + text.count('!') + text.count('?'),
        "平均词长": sum(len(word) for word in words) / len(words) if words else 0
    }


# 测试工具
sample_text = "LangChain is amazing! It makes building AI applications easy."
result = text_analyzer.invoke({"text": sample_text})
print(f"文本: {sample_text}")
print(f"分析结果: {result}")

print("\n" + "=" * 50)
print("示例3: 创建搜索工具（模拟）")
print("=" * 50)


@tool
def search_database(query: str, category: Optional[str] = None) -> str:
    """
    在数据库中搜索信息（模拟）

    Args:
        query: 搜索查询
        category: 可选的类别过滤器

    Returns:
        搜索结果
    """
    # 模拟数据库
    database = {
        "科技": ["人工智能正在改变世界", "量子计算的未来", "5G技术的应用"],
        "健康": ["健康饮食的重要性", "运动与长寿的关系", "心理健康建议"],
        "教育": ["在线学习的趋势", "STEM教育的重要性", "终身学习的价值"]
    }

    results = []

    if category and category in database:
        # 在特定类别中搜索
        for item in database[category]:
            if query.lower() in item.lower():
                results.append(f"[{category}] {item}")
    else:
        # 在所有类别中搜索
        for cat, items in database.items():
            for item in items:
                if query.lower() in item.lower():
                    results.append(f"[{cat}] {item}")

    if results:
        return "找到以下结果:\n" + "\n".join(results)
    else:
        return f"没有找到关于 '{query}' 的结果"


# 测试工具
result1 = search_database.invoke({"query": "人工智能"})
print(f"搜索 '人工智能':\n{result1}\n")

result2 = search_database.invoke({"query": "健康", "category": "健康"})
print(f"在健康类别中搜索 '健康':\n{result2}")

print("\n" + "=" * 50)
print("示例4: 将工具绑定到模型")
print("=" * 50)


@tool
def get_weather(city: str) -> str:
    """
    获取城市的天气信息（模拟）

    Args:
        city: 城市名称

    Returns:
        天气信息
    """
    # 模拟天气数据
    weather_data = {
        "北京": "晴天，温度25°C",
        "上海": "多云，温度22°C",
        "广州": "小雨，温度28°C",
        "深圳": "晴天，温度30°C"
    }

    return weather_data.get(city, f"{city}的天气信息暂时无法获取")


@tool
def get_time() -> str:
    """
    获取当前时间

    Returns:
        当前时间字符串
    """
    from datetime import datetime
    return datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")


# 创建工具列表
tools = [get_weather, get_time]

# 将工具绑定到模型
llm_with_tools = llm.bind_tools(tools)

# 调用模型（模型可以决定是否使用工具）
print("询问模型：北京今天天气如何？")
response = llm_with_tools.invoke("北京今天天气如何？")

print(f"\n模型响应类型: {type(response)}")
print(f"响应内容: {response.content}")

# 检查是否有工具调用
if hasattr(response, 'tool_calls') and response.tool_calls:
    print(f"\n模型决定使用工具:")
    for tool_call in response.tool_calls:
        print(f"- 工具名称: {tool_call['name']}")
        print(f"- 工具参数: {tool_call['args']}")

        # 执行工具调用
        if tool_call['name'] == 'get_weather':
            result = get_weather.invoke(tool_call['args'])
            print(f"- 工具结果: {result}")

print("\n" + "=" * 50)
print("示例5: 创建自定义工具类")
print("=" * 50)

from langchain_core.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class TemperatureConverterInput(BaseModel):
    """温度转换工具的输入模式"""
    temperature: float = Field(description="要转换的温度值")
    from_unit: str = Field(description="原始温度单位：'C'(摄氏度)或'F'(华氏度)")
    to_unit: str = Field(description="目标温度单位：'C'(摄氏度)或'F'(华氏度)")


class TemperatureConverter(BaseTool):
    """温度转换工具"""
    name: str = "temperature_converter"
    description: str = "转换摄氏度和华氏度之间的温度"
    args_schema: Type[BaseModel] = TemperatureConverterInput

    def _run(self, temperature: float, from_unit: str, to_unit: str) -> str:
        """同步执行工具"""
        if from_unit == to_unit:
            return f"{temperature}°{from_unit}"

        if from_unit == "C" and to_unit == "F":
            result = (temperature * 9 / 5) + 32
            return f"{temperature}°C = {result:.2f}°F"
        elif from_unit == "F" and to_unit == "C":
            result = (temperature - 32) * 5 / 9
            return f"{temperature}°F = {result:.2f}°C"
        else:
            return "错误：不支持的温度单位"

    async def _arun(self, temperature: float, from_unit: str, to_unit: str) -> str:
        """异步执行工具（可选）"""
        return self._run(temperature, from_unit, to_unit)


# 使用自定义工具
temp_converter = TemperatureConverter()
result = temp_converter.invoke({
    "temperature": 25,
    "from_unit": "C",
    "to_unit": "F"
})
print(f"温度转换结果: {result}")

print("\n" + "=" * 50)
print("Tools示例完成！")
print("=" * 50)