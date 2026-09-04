# PR 4：Course Search MCP Server 实检索骨架

## 范围

PR 4 将 Course Search MCP Server 从 PR 1 的纯 mock 工具升级为可读取 SQLite course/chunk 元数据的检索工具，支持：

1. `list_courses`：从 SQLite `courses` 表读取课程列表。
2. `search_course_material`：从 SQLite `course_chunks` 联表读取 chunk，并按课程、内容类型过滤。
3. `get_course_chunk`：按 `chunk_id` 读取单个 chunk。
4. 当 SQLite 数据库不存在或 schema 尚未初始化时，保留 PR 1 mock fallback，保证本地开发与旧测试稳定。

## 数据来源

默认读取环境变量：

```bash
DATABASE_URL=sqlite:///data/app.sqlite
```

该数据库由 PR 2 migration 与 PR 3 ingestion CLI 写入：

```bash
make ingest-import
make ingest-rebuild
```

## 检索策略

当前仍是 MVP 骨架：

- 不接入 embedding。
- 不读取 Chroma。
- 使用 SQLite 元数据和 `text_preview`。
- `search_course_material` 先应用结构化过滤，再用轻量 query token 命中率计算 score。

## 安全约束

- MCP Server 只读取 ingestion 后的 `text_preview`，不读取完整课程正文。
- 不记录 secrets。
- 未来接入用户身份后，必须在 SQL 查询层增加课程 ACL 过滤。

## 后续演进

1. 接入 Chroma / vector search。
2. 将 SQLite 过滤条件与向量召回组合为 hybrid retrieval。
3. 增加 ACL-aware retrieval。
4. 补充 retrieval trace event，用于 Agent 轨迹评估。
