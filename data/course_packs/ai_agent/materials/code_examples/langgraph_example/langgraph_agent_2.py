# ============================================
# 案例3：从头构建ReAct Agent（完全控制）
# ============================================

from typing import Annotated, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_community.chat_models import ChatTongyi
import operator

print("\n" + "=" * 60)
print("案例3: 从头构建ReAct Agent - V1.0")
print("=" * 60)


# 1. 定义State
class AgentState(TypedDict):
    """Agent状态"""
    messages: Annotated[list, add_messages]
    iterations: Annotated[int, operator.add]


# 2. 定义工具
@tool
def python_executor(code: str) -> str:
    """执行Python代码并返回结果

    Args:
        code: Python代码字符串
    """
    try:
        # 创建安全的执行环境
        safe_globals = {
            '__builtins__': {
                'print': print,
                'len': len,
                'range': range,
                'sum': sum,
                'max': max,
                'min': min,
                'abs': abs,
                'round': round,
            }
        }
        local_vars = {}

        # 执行代码
        exec(code, safe_globals, local_vars)

        # 如果有result变量，返回它
        if 'result' in local_vars:
            return f"✅ 执行成功，结果: {local_vars['result']}"
        else:
            return "✅ 代码执行成功（无返回值）"
    except Exception as e:
        return f"❌ 执行错误: {str(e)}"


@tool
def text_analyzer(text: str) -> str:
    """分析文本的统计信息

    Args:
        text: 要分析的文本
    """
    chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
    english_words = len([w for w in text.split() if any(c.isalpha() for c in w)])
    total_chars = len(text)

    return f"""📊 文本分析结果：
- 总字符数: {total_chars}
- 中文字符: {chinese_chars}
- 英文单词: {english_words}
- 平均词长: {total_chars / max(english_words, 1):.1f}"""


@tool
def data_processor(numbers: str) -> str:
    """处理数字列表并返回统计信息

    Args:
        numbers: 逗号分隔的数字，如 "1,2,3,4,5"
    """
    try:
        nums = [float(x.strip()) for x in numbers.split(',')]

        return f"""📈 数据处理结果：
- 总数: {len(nums)}
- 求和: {sum(nums)}
- 平均值: {sum(nums) / len(nums):.2f}
- 最大值: {max(nums)}
- 最小值: {min(nums)}
- 中位数: {sorted(nums)[len(nums) // 2]}"""
    except:
        return "❌ 数据格式错误，请提供逗号分隔的数字"


# 3. 创建工具节点
tools = [python_executor, text_analyzer, data_processor]
tool_node = ToolNode(tools)

# 4. 初始化模型
llm = ChatTongyi(
    model="qwen-plus",
    temperature=0.7,
    dashscope_api_key=""
)

# 绑定工具到模型
llm_with_tools = llm.bind_tools(tools)


# 5. 定义节点函数
def call_model(state: AgentState):
    """调用模型节点"""

    messages = state["messages"]
    iterations = state.get("iterations", 0)

    # 添加系统提示
    system_msg = SystemMessage(content="""你是一个专业的AI助手，可以使用工具来完成任务。

可用工具：
1. python_executor - 执行Python代码
2. text_analyzer - 分析文本
3. data_processor - 处理数据

思考流程：
1. 分析用户需求
2. 选择合适的工具
3. 使用工具并解释结果""")

    # 调用模型
    response = llm_with_tools.invoke([system_msg] + messages)

    print(f"🧠 Agent思考中... (迭代 {iterations + 1})")

    return {
        "messages": [response],
        "iterations": 1
    }


# 6. 定义路由函数
def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """判断是否继续"""

    messages = state["messages"]
    last_message = messages[-1]

    # 使用tools_condition辅助函数
    # 如果有工具调用，返回"tools"，否则返回"__end__"
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        tool_name = last_message.tool_calls[0]["name"]
        print(f"→ 调用工具: {tool_name}")
        return "tools"

    print("→ 完成任务")
    return "__end__"


# 7. 构建图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# 设置流程
workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        "__end__": END
    }
)
workflow.add_edge("tools", "agent")

# 编译
app = workflow.compile()

# 8. 测试
test_cases = [
    "帮我执行这段代码：result = sum([1, 2, 3, 4, 5])",
    "分析这段文本：LangGraph是一个强大的框架，用于构建AI应用",
    "处理这些数据：10, 20, 30, 40, 50",
]

for query in test_cases:
    print(f"\n{'=' * 60}")
    print(f"👤 用户: {query}")
    print("=" * 60)

    result = app.invoke({
        "messages": [HumanMessage(content=query)],
        "iterations": 0
    })

    # 打印最终回答
    final_msg = result["messages"][-1]
    print(f"\n✅ 最终回答:")
    print(final_msg.content)
    print(f"\n📊 统计: 共{result['iterations']}次迭代")