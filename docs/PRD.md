# 项目 PRD｜基于 LangGraph、MCP 与 RAG 的 AI Agent 课程助教系统

> 来源：飞书文档 `docx/ZqiddXokgodcbrxiSWhl1RUXgjd`（revision 5），通过 lark-cli 于 2026-07-16 拉取。

**项目一句话：** 构建一个能够理解四门 AI Agent 课程内容、检索 PPT / 讲义 / 逐字稿、回答学员问题、批改练习、规划学习路径，并通过 MCP 标准化调用工具的课程助教 Agent 系统。

---

## 1. 项目背景

课程体系围绕 AI Agent 核心能力展开：Agent 基础与 LangChain、LangGraph 与多 Agent、MCP、RAG 与向量数据库。课程材料（PPT、讲义、逐字稿、代码示例、练习、项目方案）已齐备但仍是静态资产。

常见痛点：不知道概念在哪一页讲过、无法把四门课串成完整工程链路、练习答案缺少即时反馈、代码理解停留在复制运行层面、无法判断某类 Agent 方案是否适合真实业务。

目标：把课程内容转化为可交互、可检索、可评估、可扩展的 AI Agent 教学系统。

### 项目机会

| 机会点 | 当前问题 | 项目价值 |
|-|-|-|
| 课程资产结构化 | PPT、逐字稿、讲义、代码分散，难精确检索复用 | 构建带元数据知识库，支持页码/章节定位与引用回答 |
| 学员即时答疑 | 依赖讲师，高频重复 | RAG 问答 + 助教 Agent 降低重复答疑成本 |
| 练习反馈自动化 | 人工批改反馈周期长 | Grader Agent 给出评分、诊断、改进建议 |
| 复杂技术串联 | LangGraph/MCP/RAG 被当孤立知识点 | 项目化系统串成完整工程主线 |
| 课程持续迭代 | FAQ、失败案例难成闭环 | 记录高频问题/检索失败/低质回答，反哺课程 |

## 2. 项目目标

### 2.1 产品目标
- 面向 AI Agent 课程学习场景的智能助教：课程问答、知识定位、学习路径规划、练习批改、项目辅导。
- 四门课程的 PPT/讲义/逐字稿/代码/练习沉淀为可检索、可追溯、可评估的知识库。
- 用 LangGraph 显式编排 Agent 工作流（Router、Retriever、Answer、Reviewer、Grader 等节点）。
- 用 MCP 将课程查询、代码示例、作业批改、学习路径等能力标准化为工具服务。
- 用 RAG + 向量数据库实现基于课程证据的回答，降低幻觉。

### 2.2 教学目标
- 帮助学员理解四门课关系：Agent 基础提供思想，LangGraph 提供编排，MCP 提供工具协议，RAG 提供知识增强。
- 让学员通过完整项目掌握：知识库构建 → 检索问答 → Agent 编排 → 工具调用 → 质量评估。
- 让讲师可将项目作为结课项目、课堂 Demo、作业系统和答疑工具。

### 2.3 非目标
第一阶段不追求通用企业知识库平台，不覆盖复杂权限系统、跨组织知识治理、多租户计费、全量生产级监控和大规模在线训练。MVP 重点验证课程助教场景的可用性与教学价值。

## 3. 用户与使用场景

### 3.1 目标用户

| 用户角色 | 核心诉求 | 典型问题 | 成功标准 |
|-|-|-|-|
| 课程学员 | 快速理解概念、完成练习、即时反馈 | LangGraph 为什么需要 State？MCP Server 怎么写？RAG 如何评估？ | 获得准确、可追溯、教学化回答 |
| 授课讲师 | 降低重复答疑、辅助课堂互动与作业点评 | 哪些问题问得最多？练习常见错误？ | 查看高频问题、练习反馈和课程薄弱点 |
| 助教 / 运营 | 整理问题、沉淀 FAQ、跟进进度 | 本周最困惑的知识点？哪些题需补讲？ | 导出问题汇总和改进建议 |
| 项目评审者 | 评估学员是否掌握 Agent 项目能力 | 方案是否覆盖 RAG/LangGraph/MCP/评估？ | 基于统一 Rubric 生成评审反馈 |

### 3.2 核心使用场景
- **学习前**：生成学习路径、预览四门课关系、推荐重点 PPT 页和讲义章节。
- **学习中**：回答课程概念、定位 PPT 页码/讲义段落/代码示例、解释代码与架构。
- **练习后**：批改答案、指出缺失环节与误区、给出改进版本和参考答案。
- **项目阶段**：辅助设计结课方案、检查是否覆盖四门课核心能力、生成验收 Rubric 和优化建议。

## 4. 产品范围

### 4.1 MVP 范围

| 模块 | MVP 能力 | 说明 | 优先级 |
|-|-|-|-|
| 课程资料导入 | 导入 PPT、讲义、逐字稿、代码示例 | 本地文件或预置资料目录 | P0 |
| 知识库构建 | 清洗、分块、元数据标注、Embedding、写入向量库 | 每 chunk 保留课程、页码、章节、内容类型 | P0 |
| 课程问答 | 基于 RAG 回答 | 返回结论、解释、证据来源、推荐追问 | P0 |
| 页码定位 | 定位相关 PPT 页或讲义章节 | 适合复习和备课 | P0 |
| Agentic RAG | 查询改写、检索、证据判断、回答生成、Reviewer 校验 | LangGraph 编排，避免黑盒链式 | P0 |
| 练习批改 | 对答案评分并反馈 | MVP 支持文本答案，不支持复杂代码执行判题 | P1 |
| 学习路径 | 按时间和基础推荐路线 | 30 分钟/2 小时/半天/完整四种模式 | P1 |
| MCP 工具 | 至少 Course Search MCP Server | 后续扩展 Homework/Code Example/Learning Path | P1 |
| Web UI | 聊天界面、来源面板、轨迹面板 | MVP 可简化为单页 | P1 |
| 评估报告 | 记录测试问题、检索命中、回答质量、失败案例 | 支持迭代和验收 | P1 |

### 4.2 暂不纳入范围
- 不做多租户商业化后台、复杂组织权限矩阵、大规模实时数据同步、自动训练/模型微调平台、完全自动化代码运行评测沙箱（除非进阶版本）。

## 5. 核心功能需求

### 5.1 课程知识问答
| 编号 | 需求 | 验收标准 |
|-|-|-|
| QA-001 | 支持自然语言提问（Agent/LangChain/LangGraph/MCP/RAG/向量库等主题） | 能识别课程相关问题并进入 RAG 流程 |
| QA-002 | 回答含简短结论、展开解释、关键要点、来源信息 | 至少 1 条课程来源，含课程名、页码或章节 |
| QA-003 | 证据不足时明确说明"证据不足"而非编造 | 拒答率达预期，不输出虚假页码 |
| QA-004 | 支持推荐追问 | 每次回答后给 2–3 个相关追问 |

### 5.2 PPT 与讲义定位
| 编号 | 需求 | 验收标准 |
|-|-|-|
| LOC-001 | 按关键词/概念/问题定位材料 | "FastMCP 怎么实现" 返回 PPT3 相关页和代码讲解 |
| LOC-002 | 返回多候选并按相关性排序 | 含标题、摘要、课程、页码、内容类型 |
| LOC-003 | 区分 PPT/逐字稿/讲义/代码示例 | content_type 字段准确 |

### 5.3 学习路径规划
| 编号 | 需求 | 验收标准 |
|-|-|-|
| PLAN-001 | 输入用户基础（初学者/Python 基础/熟悉 LLM/后端工程） | 按基础调整解释粒度和顺序 |
| PLAN-002 | 输入可用时间（30 分钟/2 小时/半天/完整） | 生成不同粒度计划 |
| PLAN-003 | 计划含推荐章节、预计耗时、学习目标、检查问题 | 计划可执行而非泛泛建议 |

### 5.4 练习批改
| 编号 | 需求 | 验收标准 |
|-|-|-|
| GRADE-001 | 输入练习题和学员答案 | 识别题目目标，判断答案覆盖度 |
| GRADE-002 | 输出评分、优点、缺失点、风险点、改进建议、参考答案 | 维度清晰，反馈可行动 |
| GRADE-003 | 按课程模块用不同 Rubric | LangGraph 题看状态/节点/边/退出条件；RAG 题看分块/检索/Rerank/引用/评估 |

### 5.5 Agentic RAG 工作流
| 编号 | 需求 | 验收标准 |
|-|-|-|
| GRAPH-001 | 用 LangGraph 实现显式状态流转 | 存在 State、Node、Edge、Conditional Edge、END |
| GRAPH-002 | 支持 Query Rewrite | 首次检索不足时改写并再检索 |
| GRAPH-003 | 支持最大重试次数 | retry_count 达阈值必须退出，不允许无限循环 |
| GRAPH-004 | 支持 Reviewer 校验 | 检查是否基于证据、是否覆盖问题、是否明显幻觉 |

### 5.6 MCP 工具化
| 编号 | 工具 | 能力 | MVP 是否必需 |
|-|-|-|-|
| MCP-001 | Course Search Server | search_course_material、get_slide_detail、get_transcript_section | 是 |
| MCP-002 | Homework Grading Server | grade_answer、get_reference_answer、list_homework | 否，V1 |
| MCP-003 | Code Example Server | search_code_example、get_code_snippet、explain_code | 否，V1 |
| MCP-004 | Learning Path Server | generate_learning_plan、recommend_next_topic | 否，V2 |

## 6. 信息架构与页面设计

### 6.1 页面模块
| 页面 | 核心功能 | 主要用户 | 优先级 |
|-|-|-|-|
| 首页 / Chat | 输入问题、展示回答、追问建议 | 学员、讲师 | P0 |
| 来源面板 | 展示命中 PPT 页/讲义段落/逐字稿/代码 | 学员、讲师 | P0 |
| Agent 轨迹面板 | 展示 Router/Retriever/Reviewer/Retry 执行过程 | 讲师、研发、评审者 | P1 |
| 练习批改页 | 提交答案、查看评分与反馈 | 学员、助教 | P1 |
| 课程知识库页 | 浏览课程、章节、PPT 页、资料状态 | 讲师、运营 | P1 |
| 评估报告页 | 查看测试问题、检索质量、回答质量、失败案例 | 讲师、研发 | P2 |

### 6.2 Chat 回答结构
推荐：先结论再解释；先回答再补课程定位；必须展示来源，不确定时明确证据不足。
1. 简短结论（1–3 句）
2. 展开解释（概念、机制、工程取舍）
3. 课程来源（课程名、PPT 页码、讲义章节或逐字稿片段）
4. 继续学习（下一页/下一节/相关练习）
5. 追问建议（2–3 个）

## 7. 数据与知识库设计

### 7.1 数据来源
| 数据类型 | 来源 | 用途 | 处理方式 |
|-|-|-|-|
| PPT | PPT1–PPT4 HTML 课件 | 课程结构、页码定位、图示说明 | 按 section 抽取标题、正文、代码、图示描述 |
| 讲义 | 完整授课讲义文档 | 概念解释和讲授依据 | 按课程、章节、页面切分 |
| 逐字稿 | 逐页授课稿 | 回答时提供教学化解释 | 按页码与知识点建立映射 |
| 代码示例 | 课程代码块和示例工程 | 代码解释、作业辅导 | 按主题、语言、依赖、输入输出标注 |
| 练习题 | 课堂互动和作业 | 练习批改和能力评估 | 建立题目、参考答案、Rubric |
| FAQ | 课堂高频问题 | 提升常见问题稳定性 | 定期从日志整理更新 |

### 7.2 知识片段元数据
```json
{
  "doc_id": "ppt3_slide_08_transcript_01",
  "course_id": "ppt3_mcp",
  "course_name": "PPT3：MCP 与 Agent 工具生态",
  "slide_no": 8,
  "section": "MCP Server",
  "content_type": "slide_transcript",
  "text": "MCP Server 用于向 Agent 暴露工具、资源和 Prompt...",
  "keywords": ["MCP", "Server", "Tools", "Resources", "Prompts"],
  "source_path": "frontend_slides_03_mcp_agent_ppt1_style.html",
  "version": "v1"
}
```

### 7.3 分块策略
| 内容类型 | 分块方式 | 推荐粒度 | 注意事项 |
|-|-|-|-|
| PPT 页面 | 一页一主 chunk，复杂页按图示/代码/要点拆 | 300–800 中文字 | 必须保留页码 |
| 讲义 | 按 h2/h3 章节切分 | 500–1000 中文字 | 避免跨主题切分 |
| 逐字稿 | 按 PPT 页或段落切分 | 400–900 中文字 | 保留口吻但去重 |
| 代码示例 | 按函数/类/文件/完整案例切分 | 一个完整逻辑单元 | 同时生成自然语言摘要 |
| 练习题 | 题目/参考答案/评分标准分开 | 按题目粒度 | 便于 Grader 调用 |

## 8. Agent 与工作流设计

### 8.1 Agent 角色
| Agent | 职责 | 输入 | 输出 |
|-|-|-|-|
| Router Agent | 判断意图与任务类型 | 用户问题 | direct_answer、rag_answer、locate_material、grade_homework、learning_plan、tool_call |
| Planner Agent | 拆解复杂学习/项目问题 | 目标、约束 | 步骤计划、所需资料、执行顺序 |
| Retriever Agent | 检索知识库 | 查询、过滤条件 | 相关片段和来源 |
| Answer Agent | 生成教学化回答 | 问题、证据、上下文 | 结构化答案 |
| Reviewer Agent | 检查答案质量 | 答案、证据、原问题 | 通过、修改建议或拒答建议 |
| Grader Agent | 批改练习 | 题目、答案、Rubric | 评分、诊断、建议、参考答案 |
| Tool Agent | 调用 MCP 工具 | 工具请求 | 结构化工具结果 |

### 8.2 LangGraph State 设计
```python
class TutorState(TypedDict):
    user_query: str
    task_type: str
    rewritten_query: str
    retrieved_docs: list[dict]
    answer: str
    review_result: dict
    retry_count: int
    max_retry: int
    citations: list[dict]
    final_response: str
```

### 8.3 关键流程
| 流程 | 节点顺序 | 退出条件 | 适用场景 |
|-|-|-|-|
| 直接回答 | Router → Answer → Reviewer → Final | Reviewer 通过 | 定义、简单概念 |
| RAG 问答 | Router → Retrieve → Generate → Reviewer → Final | 证据充分且通过 | 需引用资料的问题 |
| Agentic RAG | Router → Rewrite → Retrieve → Grade Docs → Generate → Reviewer → Final | 证据充分或达最大重试 | 复杂问题、首检不足 |
| 练习批改 | Router → Load Rubric → Grade → Reviewer → Final | 评分与反馈完整 | 作业、练习、项目方案 |
| 学习路径 | Router → Planner → Retrieve Key Topics → Generate Plan → Reviewer → Final | 计划覆盖时间/目标/检查点 | 个性化学习建议 |

## 9. 技术方案约束

### 9.1 推荐技术栈
| 层级 | 推荐选型 | 说明 | MVP 选择 |
|-|-|-|-|
| 后端 API | Python + FastAPI | 快速构建 Agent 服务与工具 API | 是 |
| Agent 编排 | LangGraph | 显式状态、条件边、循环控制、可观测轨迹 | 是 |
| RAG 框架 | LangChain 组件或自定义轻量 Pipeline | Loader、Splitter、Retriever 等 | 是 |
| 向量数据库 | Chroma / FAISS | 教学版部署简单 | Chroma |
| 结构化存储 | SQLite / PostgreSQL | 元数据、日志、评估结果 | SQLite |
| MCP | MCP Server | 课程查询、作业批改工具化 | Course Search Server |
| 前端 | React / Next.js | Chat UI、来源面板、轨迹面板 | React 单页 |
| 部署 | Docker Compose | 课程演示与本地运行 | 是 |

### 9.2 非功能要求
| 类别 | 要求 | MVP 指标 | 说明 |
|-|-|-|-|
| 准确性 | 回答尽量基于课程资料 | 关键问题正确率 ≥ 80% | 错误答案进失败案例库 |
| 可追溯性 | 重要回答展示来源 | 来源覆盖率 ≥ 90% | 来源含课程和页码/章节 |
| 延迟 | 普通问答可交互 | P95 ≤ 10 秒 | 复杂多 Agent 可更长 |
| 稳定性 | 工作流不无限循环 | 循环节点必须有 max_retry | 异常返回可解释失败原因 |
| 可观测性 | 记录检索/工具调用/Reviewer 结果 | 每请求保留 trace | 用于评估和复盘 |
| 安全性 | 不暴露未授权资料，不执行危险代码 | MVP 禁止任意代码执行 | 代码解释与运行分阶段 |

## 10. 评估指标

### 10.1 产品指标
| 指标 | 定义 | 目标 |
|-|-|-|
| 问题解决率 | 用户认为回答解决问题的比例 | ≥ 80% |
| 来源可用率 | 来源能定位原文的比例 | ≥ 90% |
| 练习反馈满意度 | 学员认为反馈有帮助的比例 | ≥ 80%（V1） |
| 学习路径采纳率 | 用户继续使用推荐路径的比例 | ≥ 50% |

### 10.2 RAG 指标
| 指标 | 定义 | 目标 |
|-|-|-|
| Recall@K | 正确资料出现在前 K 个结果中 | Recall@5 ≥ 85% |
| MRR | 正确资料排名靠前 | ≥ 0.7 |
| Faithfulness | 回答忠于检索证据 | ≥ 85% |
| Citation Accuracy | 引用真实支持回答 | ≥ 90% |

### 10.3 Agent 指标
| 指标 | 定义 | 目标 |
|-|-|-|
| Task Success Rate | 任务最终完成率 | ≥ 80% |
| Tool Call Accuracy | 工具选择和参数正确 | ≥ 85% |
| Loop Rate | 异常循环比例 | ≤ 1% |
| Average Steps | 平均执行节点数 | 按任务类型分层统计 |

## 11. 版本规划

- **MVP：课程 RAG 助教** — 导入四门课资料、构建知识库、基础问答、返回来源、LangGraph Agentic RAG、Reviewer 校验、最小 Web Chat UI。
- **V1：练习与项目辅导** — 练习批改 Agent、课程 Rubric、学习路径规划、项目方案审查、高频问题沉淀。
- **V2：MCP 工具体系** — Course Search / Homework Grading / Code Example MCP Server、Agent 经 MCP 调用、展示工具调用轨迹。
- **V3：教学运营与评估** — 标准评测集、课程薄弱点报告、高频问题汇总、知识库版本管理、结课评分面板。

## 12. 里程碑计划
| 阶段 | 周期 | 目标 | 交付物 |
|-|-|-|-|
| 1 资料处理 | 第 1 周 | 解析、清洗、分块、元数据设计 | 离线索引脚本、知识片段 JSON、初版向量库 |
| 2 基础 RAG | 第 2 周 | 课程问答、来源返回、基础 API | RAG API、检索接口、测试问题集 |
| 3 LangGraph 工作流 | 第 3 周 | Router/Retriever/Generate/Reviewer/Retry | Agentic RAG 图、Trace 日志、失败兜底 |
| 4 MCP 工具 | 第 4 周 | Course Search MCP Server + Agent 接入 | MCP Server、工具 schema、调用示例 |
| 5 前端 Demo | 第 5 周 | Chat UI、来源面板、轨迹面板 | 可演示 Web 应用 |
| 6 评估优化 | 第 6 周 | 评测、Prompt/分块优化、验收材料 | 评估报告、演示脚本、结课验收 Rubric |

## 13. 验收标准

### 13.1 基础通过
- 导入课程资料并完成向量化；用户可提问并获回答；回答返回课程来源；至少一个 LangGraph 工作流；至少一个 MCP Tool/Server；至少一组课程评测问题；证据不足时的拒答机制。

### 13.2 优秀
- Query Rewrite 和检索重试；Reviewer 自动审查；练习批改；学习路径规划；Agent 执行轨迹展示；检索质量和回答质量评估。

### 13.3 卓越
- 多 MCP Server 插拔；知识库版本管理；课程 FAQ 自动沉淀；项目结课评分与报告生成；Human-in-the-loop 审核节点。

## 14. 风险与应对
| 风险 | 表现 | 影响 | 应对 |
|-|-|-|-|
| RAG 幻觉 | 回答看似合理但资料不支持 | 误导学员 | 强制来源、Reviewer 校验、证据不足拒答 |
| 检索召回不足 | 相关资料未召回 | 回答不完整 | 优化分块、增关键词、混合检索、Query Rewrite |
| 多 Agent 延迟高 | 复杂流程慢 | 影响体验 | 按复杂度路由，简单问题不走多 Agent |
| 循环失控 | 反复改写检索 | 成本/延迟不可控 | max_retry + 明确 END |
| MCP 工具边界模糊 | 工具既检索又回答 | 职责混乱难调试 | 工具只返事实和结构化结果，回答由 Answer Agent 生成 |
| 课程资料版本变化 | 更新后来源不一致 | 引用失效 | 引入版本号和重新索引流程 |

## 15. 开放问题
1. 课程资料以本地文件、飞书文档、知识库还是混合方式接入？
2. 是否要求来源可点击跳转到原始 PPT/讲义？
3. MVP 是否必须支持代码运行，还是仅代码解释？
4. 练习批改是否需和人工评分对齐？是否有历史样本？
5. 是否需要记录学员个人学习进度？隐私和权限边界？
6. 演示环境是本地 Docker Compose 还是共享服务器？

## 16. 附录：典型用户问题
| 场景 | 用户问题 | 期望行为 |
|-|-|-|
| 概念问答 | LangGraph 和 LangChain 的区别？ | 解释差异、适用场景、定位来源 |
| 页码定位 | MCP 的 Tools/Resources/Prompts 在哪页讲过？ | 返回 PPT3 相关页和讲义章节 |
| 工程设计 | 做一个 RAG Agent 怎么设计流程？ | 生成方案，说明分块/检索/Rerank/Reviewer/评估 |
| 练习批改 | "问题→向量检索→LLM 回答" 够吗？ | 评分，指出缺离线索引/查询改写/Rerank/引用/评估 |
| 学习路径 | 只有 2 小时怎么学完四门课？ | 按时间生成压缩计划 |
| 项目验收 | 结课方案是否覆盖四门课？ | 按 Rubric 检查 Agent/LangGraph/MCP/RAG/评估 |
