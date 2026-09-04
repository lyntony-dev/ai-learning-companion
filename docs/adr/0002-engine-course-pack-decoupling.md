# ADR-0002：学习引擎与课程包解耦(双层架构)

- 状态：已接受
- 日期：2026-07-16

## 背景

原 PRD 把系统定位成"AI Agent 课程的问答接口",课程内容与系统逻辑深度耦合(`course_id` 硬编码四门课、Rubric 按 AI Agent 模块写死、结课项目特指 Agent 工程)。产品方将愿景升级为 Level 2：**一个"学什么都陪你到会"的 AI 学习伙伴,对每门课都成立,AI Agent 课程是第一个验证实例。**

如果沿用耦合设计,愿景放大将无法落地——接第二门课需要改引擎。

## 决策

系统分为两层,强制解耦:

- **学习引擎 (Learning Engine)**：领域无关。包含陪伴式对话、Learner Model、训练闭环、项目闭环、教学洞察、Agentic RAG 编排。引擎代码中**禁止**出现任何 AI Agent 课程专属的硬编码(课程名、知识点、Rubric 维度)。
- **课程包 (Course Pack)**：领域特定、可插拔。包含该课程的资料与知识库、知识点体系(taxonomy)、评分 Rubric、结课项目定义。以数据/配置形式加载,而非写进引擎逻辑。

第一个课程包 = AI Agent 课程(LangChain / LangGraph / MCP / RAG)。

## 权衡

- **成本**：需要提前定义"课程包"的接口边界(资料 schema、taxonomy schema、Rubric schema、项目定义 schema),比直接写死复杂;MVP 只有一个课程包却要付抽象成本。
- **收益**：掀掉产品天花板;解耦本身是良好架构(内容与逻辑分离);未来接新课 = 加一个课程包目录,引擎零改动。
- **被否决的方案**：保持 PRD 的耦合设计,MVP 更快但焊死愿景。否决理由:与已确认的 Level 2 愿景直接冲突。

## 边界(避免过度抽象)

- MVP **不**接第二门课,不构建课程包市场/上传后台。抽象只做到"引擎不含领域硬编码 + 课程包是独立数据目录"这一层,不做更多。
- 课程包 schema 先服务 AI Agent 课的真实需要,不为想象中的第二门课过度设计;第二门课出现时再重构 schema 是可接受的。

## 影响

- 数据模型:`Course`/`CourseChunk`/`Rubric`/`Homework` 等实体需带 `course_pack_id`,并从课程包目录加载。
- 目录结构:`data/course_packs/<pack_id>/` 承载单个课程包;AI Agent 课程资料从 `data/raw/` 迁移到 `data/course_packs/ai_agent/`。
- 引擎配置:课程包通过 manifest 声明,引擎启动时加载,不写死。
