"""领域无关学习引擎 (DESIGN §2/§3)。

编排层(orchestration)承载 LangGraph 主图与子图;retrieval 为检索适配器。
引擎不 import 任何具体课程常量,课程内容经 CoursePack 数据注入。
"""
