# PR 6：FastAPI 核心接口

## 范围

PR 6 将 PR 5 的课程助教 Agent 主链路挂载到 FastAPI，提供 MVP-B 可演示的核心后端接口：

- `POST /api/chat`
- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}/messages`
- `GET /api/traces/{trace_id}`

## 设计说明

当前版本仍保持确定性本地骨架：`POST /api/chat` 调用 `CourseTutorAgent`，生成答案、citation 与节点 trace，并将会话、消息和 trace 摘要写入 SQLite。

为降低未来替换成本，接口层只依赖 Agent 的稳定 request/response 边界。后续接入真实 LangGraph runtime、MCP client、LLM provider 时，可以优先替换 Agent 内部实现，而不破坏 API 合约。

## 数据写入策略

`POST /api/chat` 会写入：

1. conversation summary
2. user message summary
3. assistant message summary
4. trace summary
5. trace event summaries

## 安全约束

- 默认只持久化摘要、结构化 citation 和 trace metadata。
- 不存完整 prompt。
- 不存完整用户输入。
- 不存完整模型输出。
- 不存完整 retrieved chunk text。
- 不存 secrets 或 Authorization header。

## 当前限制

- 未接入真实鉴权，`user_id` 仍由请求或默认配置传入。
- `CourseTutorAgent` 仍使用本地 mock retriever adapter。
- trace latency 仅记录请求总耗时，节点级 latency 暂为默认值。
- conversation title 使用问题摘要生成，后续可替换为 LLM 标题生成。

## 后续演进

1. 增加认证态用户上下文，禁止客户端伪造 `user_id`。
2. 将 Agent retriever 替换为真实 Course Search MCP client。
3. 将 trace 写入和请求链路打通统一 request id。
4. 增加分页、游标和 conversation ownership 校验。
5. 增加错误态 trace 写入和统一异常处理。
