# 实现决策清单

## MVP 范围

- 采用 MVP-B：课程助教可演示版。
- 优先演示课程问答、可追溯引用、Agent Trace 与基础工程可维护性。
- PR 1 只创建工程骨架，不提前实现 ingestion、真实 RAG、LangGraph 主链路或真实 `/api/chat`。

## Agent 编排

- 主链路：`Router → Query Rewrite → Retrieve → Evidence Check → Generate → Review → Final`。
- Evidence insufficient 时最多重试 1 次 `Query Rewrite + Retrieve`。
- Review failed 时最多重试 1 次 `Generate`。
- LLM Review 默认关闭，MVP 先采用规则 Review。

## RAG 与检索

- MVP 使用本地课程材料导入。
- 采用中粒度索引。
- 检索策略：向量检索 + keyword weighting + metadata filter + title/section/content_type boost。
- MVP 不做 rerank，但保留 rerank 接口。
- Citation 必须绑定真实 retrieved chunk。

## MCP 设计

- PR 1 创建独立 Course Search MCP mock server。
- 工具包括：`list_courses`、`search_course_material`、`get_course_chunk`。
- 真实 ACL、SQLite、Chroma 与 LangGraph 接入留到后续 PR。

## API 设计

- PR 1 提供 `/healthz` 与 `/api/version`。
- 后续提供：`POST /api/chat`、`GET /api/conversations`、`GET /api/conversations/{conversation_id}`、`GET /api/traces/{trace_id}`、`GET /api/courses`。
- `stream=false` 为默认行为；`stream=true` 可降级为非流式并返回 `streaming_degraded=true`。

## 前端设计

- React 单页应用。
- 三栏布局：左侧课程/会话，中间 Chat，右侧 Sources 与 Agent Trace。
- PR 1 使用静态 mock 数据。

## 安全与合规

- `.env` 不提交。
- 不记录 secrets、Authorization header、完整 prompt、完整用户输入、完整模型输出、完整 chunk text。
- `TRACE_DEBUG_FULL=true` 仅允许本地环境。
- Course Search MCP 后续必须应用 ACL filter。

## 可观测性

- 后续记录 node-level trace、tool-call trace、retrieval event、review event、prompt version、token usage summary。
- 日志带 `request_id` / `trace_id`。
