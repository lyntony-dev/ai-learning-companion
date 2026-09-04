# ADR-0005：引擎状态持久化——规范化领域表 + LangGraph checkpointer 分离

- 状态：已接受
- 日期：2026-07-16

## 背景

口径 2 要求 Learner Model、项目里程碑状态机真实持久化，教学洞察(T)能按 course 做 per-course 聚合。技术栈已定 SQLite。需要确定业务领域数据如何建模，以及是否引入 LangGraph 自带的会话级 checkpointer。

两个正交维度：

- **会话级图状态**：LangGraph 的 `SqliteSaver` checkpointer 存"图执行 State 快照"，服务断点续跑/多轮记忆。
- **业务领域数据**：掌握度、里程碑、做题结果、题库——是长期领域资产，需可 SQL 查询与聚合。

候选：A 全塞 JSON 大 blob（聚合无法用 SQL，V2 崩）；B 规范化领域表 + checkpointer 分离（采纳）；C 直接上 Postgres+重 ORM（违背已定栈，MVP 过重）。

## 决策

- **业务库（规范化领域表）**，关键表：
  - `learner`：学习者身份。
  - `mastery(learner_id, topic_id, level, source, updated_by, updated_at)`：掌握度按 (learner, topic) 建行；`source` 区分系统推断/讲师修正，`updated_by` 记修正者。
  - `milestone_progress(learner_id, course_pack_id, milestone, status, artifact_summary, updated_at)`：里程碑状态机；`artifact_summary` 为 V2 产出物接入预留字段。
  - `exercise_attempt(learner_id, question_id, topic_id, score, feedback, created_at)`：做题结果。
  - `question_bank(question_id, course_pack_id, topic_id, source, approved_by, ...)`：题库；`source` 区分预置/LLM 生成，`approved_by` 支撑"讲师审核沉淀"演进线。
  - `qa_history`：问答历史（Learner Model 组成部分）。
  - `topic_id` / `course_pack_id` 建外键与索引，使 T 的 per-course 聚合 = `GROUP BY topic_id`（一句 SQL）。
- **会话库**：LangGraph `SqliteSaver` 独立管图 checkpoint，与业务库物理分离（独立 db 文件），互不污染。
- **ORM**：SQLModel（Pydantic + SQLAlchemy，与 FastAPI 同源，类型友好）。

## 权衡

- **成本**：前期多定义几张表与迁移；需维护两个 SQLite 文件（业务 + checkpoint）。
- **收益**：Learner Model 可查；教学洞察聚合天然是 SQL；每加一块能力=加表，扩展干净；会话状态与领域数据解耦，各自演进。
- **被否决的方案**：A（JSON blob，聚合不可 SQL 化）；C（Postgres+重 ORM，MVP 过重且违背栈）。

## 影响

- 需建 SQLModel 领域模型 + 迁移；`data/` 下区分业务库与 checkpoint 库（均 gitignore）。
- 教学洞察读模型直接查业务库做 per-course 聚合，不进 StateGraph。
- SQLite 单写入并发有限，V2 高并发时可平滑迁 Postgres（SQLModel/SQLAlchemy 层不变）。
