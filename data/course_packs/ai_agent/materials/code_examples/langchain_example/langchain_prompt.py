"""
LangChain教程 - 1. 提示词模板（Prompt Templates）基础示例

本示例展示如何使用LangChain的提示词模板功能
"""

import os
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_community.chat_models.tongyi import ChatTongyi

# 加载环境变量
load_dotenv()

# 从环境变量获取API密钥
api_key = os.getenv("DASHSCOPE_API_KEY")
print(api_key)
# 初始化通义千问模型
llm = ChatTongyi(
    model="qwen-turbo",
    dashscope_api_key=api_key,
    temperature=0.7,
    streaming=False
)

print("=" * 50)
print("示例1: 基础字符串模板")
print("=" * 50)

# 创建简单的提示词模板
simple_template = PromptTemplate.from_template(
    "请用{language}语言介绍一下{topic}，不超过100字。"
)

# 格式化模板
prompt = simple_template.format(language="中文", topic="人工智能")
print(f"\n生成的提示词:\n{prompt}\n")

# 使用LLM生成回答
response = llm.invoke(prompt)
print(f"模型回答:\n{response.content}\n")


print("=" * 50)
print("示例2: 多变量提示词模板")
print("=" * 50)

# 创建包含多个变量的模板
story_template = PromptTemplate(
    input_variables=["character", "setting", "conflict"],
    template="""
请创作一个短篇故事，要求如下：
- 主角：{character}
- 场景：{setting}
- 冲突：{conflict}

故事要生动有趣，字数控制在150字以内。
    """
)

# 使用模板
prompt = story_template.format(
    character="一只会说话的猫",
    setting="未来城市",
    conflict="寻找失落的记忆芯片"
)

print(f"生成的提示词:\n{prompt}\n")

response = llm.invoke(prompt)
print(f"模型回答:\n{response.content}\n")


print("=" * 50)
print("示例3: ChatPromptTemplate（聊天模板）")
print("=" * 50)

# 创建聊天提示词模板
chat_template = ChatPromptTemplate.from_messages([
    ("system", "你是一位{role}，擅长用简洁易懂的方式解释复杂概念。"),
    ("human", "请解释一下：{concept}"),
])

# 格式化消息
messages = chat_template.format_messages(
    role="物理学教授",
    concept="量子纠缠"
)

print("生成的消息列表:")
for msg in messages:
    print(f"- {msg.type}: {msg.content}")

# 使用LLM生成回答
response = llm.invoke(messages)
print(f"\n模型回答:\n{response.content}\n")


print("=" * 50)
print("示例4: 部分变量模板（Partial Variables）")
print("=" * 50)

from datetime import datetime

# 创建带有部分预填充变量的模板
partial_template = PromptTemplate(
    template="今天是{date}，请告诉我关于{event}的{info_type}。",
    input_variables=["event", "info_type"],
    partial_variables={
        "date": datetime.now().strftime("%Y年%m月%d日")
    }
)

# 只需要提供剩余的变量
prompt = partial_template.format(
    event="人工智能发展",
    info_type="最新进展"
)

print(f"生成的提示词:\n{prompt}\n")

response = llm.invoke(prompt)
print(f"模型回答:\n{response.content}\n")


print("=" * 50)
print("示例5: Few-shot提示词模板")
print("=" * 50)

# 创建few-shot示例模板
examples = [
    {"input": "开心", "output": "我今天非常开心！😊"},
    {"input": "难过", "output": "我感到有些难过... 😢"},
]

example_template = PromptTemplate(
    input_variables=["input", "output"],
    template="情绪: {input}\n表达: {output}"
)

# 创建包含示例的主模板
few_shot_template = ChatPromptTemplate.from_messages([
    ("system", "你是一个情绪表达助手，帮助用户用合适的方式表达情绪。以下是一些示例："),
    ("human", "\n\n".join([example_template.format(**ex) for ex in examples])),
    ("human", "现在，请帮我表达这个情绪: {emotion}")
])

# 使用模板
messages = few_shot_template.format_messages(emotion="兴奋")

response = llm.invoke(messages)
print(f"模型回答:\n{response.content}\n")


print("=" * 50)
print("提示词模板示例完成！")
print("=" * 50)