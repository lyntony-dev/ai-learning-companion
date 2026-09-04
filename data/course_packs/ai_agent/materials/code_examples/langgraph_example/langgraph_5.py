# ============================================
# 案例6：完整生产级系统 - 智能编程助手
# ============================================

import os
from typing import Literal, Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END, MessagesState
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.llms import Tongyi
from langchain_core.tools import tool
import operator

print("\n" + "=" * 60)
print("案例6: 智能编程助手 - 完整系统")
print("=" * 60)

os.environ["DASHSCOPE_API_KEY"] = ""

# 1. 初始化不同温度的模型
analyzer_llm = Tongyi(model="qwen-plus", temperature=0.3)  # 分析器
coder_llm = Tongyi(model="qwen-max", temperature=0.7)  # 代码生成
reviewer_llm = Tongyi(model="qwen-plus", temperature=0.5)  # 代码审查


# 2. 定义工具
@tool
def run_python_code(code: str) -> str:
    """运行Python代码并返回结果

    Args:
        code: Python代码字符串
    """
    try:
        # 安全执行（实际生产环境需要沙箱）
        local_vars = {}
        exec(code, {"__builtins__": __builtins__}, local_vars)

        # 获取输出
        output = local_vars.get("result", "代码执行成功，无返回值")
        return f"✅ 执行成功:\n{output}"
    except Exception as e:
        return f"❌ 执行错误:\n{str(e)}"


# 3. 定义状态
class CodingState(MessagesState):
    task_type: Literal["generate", "debug", "explain", "optimize"]
    code: str
    review_result: str
    iteration: Annotated[int, operator.add]
    max_iterations: int


# 4. 任务分析节点
def analyze_task_node(state: CodingState):
    """分析用户请求的任务类型"""

    user_request = state["messages"][-1].content

    prompt = f"""分析以下编程请求的类型，只返回一个词：
- generate: 生成新代码
- debug: 调试错误代码
- explain: 解释代码
- optimize: 优化代码

请求：{user_request}

类型："""

    task_type = analyzer_llm.invoke(prompt).strip().lower()

    if task_type not in ["generate", "debug", "explain", "optimize"]:
        task_type = "generate"

    print(f"\n🎯 任务类型: {task_type}")

    return {"task_type": task_type}


# 5. 代码生成节点
def code_generation_node(state: CodingState):
    """生成代码"""

    user_request = state["messages"][-1].content

    prompt = f"""你是一个Python编程专家。根据需求生成高质量代码。

需求：{user_request}

要求：
1. 代码要清晰、规范
2. 包含必要的注释
3. 包含使用示例
4. 确保代码可执行

请生成代码："""

    code = coder_llm.invoke(prompt)

    print(f"\n💻 代码生成完成")

    return {
        "code": code,
        "messages": [AIMessage(content=f"我已经生成了代码：\n\n```python\n{code}\n```")]
    }


# 6. 代码审查节点
def code_review_node(state: CodingState):
    """审查代码质量"""

    code = state["code"]

    prompt = f"""你是一个资深代码审查专家。审查以下Python代码：

{code}

从以下维度评分（1-10分）：
1. 正确性 - 逻辑是否正确
2. 可读性 - 代码是否清晰
3. 性能 - 是否高效
4. 规范性 - 是否符合PEP8

返回格式：
正确性: X分
可读性: X分
性能: X分
规范性: X分
总评: 如果低于8分需要改进

审查结果："""

    review = reviewer_llm.invoke(prompt)

    print(f"\n📋 代码审查完成")
    print(f"审查结果:\n{review}")

    return {"review_result": review}


# 7. 代码优化节点
def code_optimize_node(state: CodingState):
    """优化代码"""

    code = state["code"]
    review = state["review_result"]

    prompt = f"""根据审查意见优化代码：

原代码：
{code}

审查意见：
{review}

请提供优化后的代码："""

    optimized_code = coder_llm.invoke(prompt)

    print(f"\n🔧 代码优化完成")

    return {
        "code": optimized_code,
        "iteration": 1,
        "messages": [AIMessage(content=f"代码已优化：\n\n```python\n{optimized_code}\n```")]
    }


# 8. 路由函数
def route_by_task(state: CodingState) -> str:
    """根据任务类型路由"""
    return state["task_type"]


def check_review_result(state: CodingState) -> Literal["optimize", "done"]:
    """检查审查结果"""
    review = state["review_result"]
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", 2)

    # 如果提到"需要改进"且未超过最大迭代次数
    if "需要改进" in review and iteration < max_iter:
        return "optimize"
    return "done"


# 9. 构建图
workflow = StateGraph(CodingState)

# 添加节点
workflow.add_node("analyze", analyze_task_node)
workflow.add_node("generate", code_generation_node)
workflow.add_node("review", code_review_node)
workflow.add_node("optimize", code_optimize_node)

# 构建流程
workflow.add_edge(START, "analyze")

# 根据任务类型路由
workflow.add_conditional_edges(
    "analyze",
    route_by_task,
    {
        "generate": "generate",
        "debug": "generate",  # 简化处理
        "explain": "generate",  # 简化处理
        "optimize": "generate"  # 简化处理
    }
)

workflow.add_edge("generate", "review")

# 根据审查结果决定是否优化
workflow.add_conditional_edges(
    "review",
    check_review_result,
    {
        "optimize": "optimize",
        "done": END
    }
)

# 优化后再次审查
workflow.add_edge("optimize", "review")

app = workflow.compile()

# 10. 测试
test_requests = [
    "写一个快速排序的Python实现",
    "写一个计算斐波那契数列的函数"
]

for request in test_requests:
    print(f"\n{'=' * 60}")
    print(f"👤 需求: {request}")
    print("=" * 60)

    result = app.invoke({
        "messages": [HumanMessage(content=request)],
        "task_type": "generate",
        "code": "",
        "review_result": "",
        "iteration": 0,
        "max_iterations": 2
    })

    print(f"\n📊 最终结果:")
    print(f"总迭代次数: {result['iteration']}")
    print(f"\n最终代码:\n```python\n{result['code']}\n```")