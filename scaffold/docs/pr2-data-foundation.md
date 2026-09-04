# PR 2：数据基础骨架

## 范围

PR 2 在 PR 1 工程骨架基础上补充数据基础设施：

1. SQLite schema migration。
2. conversation/message 元数据表。
3. course/chunk 元数据表。
4. trace/trace_event 摘要表。
5. eval_case 表。
6. TraceRepository 示例。
7. 本地数据库初始化接口 `/api/admin/db/init`。

## 安全约束

- trace 表默认只存摘要和结构化 metadata。
- 不存完整 prompt。
- 不存完整用户输入。
- 不存完整模型输出。
- 不存完整 retrieved chunk text。
- 不存 secrets 或 Authorization header。

## 非目标

- 不接入真实 LangGraph。
- 不接入真实 Chroma。
- 不实现真实 ingestion CLI。
- 不实现真实 `/api/chat`。
- `/api/admin/db/init` 仅作为本地/admin 骨架，非本地部署前必须增加鉴权。
