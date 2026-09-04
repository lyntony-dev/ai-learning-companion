# 已知限制

## PR 1 限制

1. 后端只包含健康检查与版本接口，没有真实 `/api/chat`。
2. Course Search MCP Server 只返回 mock 数据，没有连接 SQLite、Chroma 或真实课程材料。
3. 前端是静态 demo UI，没有真实 API 请求。
4. `packages/shared` 只提供 schema/常量占位，不作为正式发布包。
5. `docker-compose.yml` 仅用于后续手动开发，PR 1 不启动任何网络监听进程。
6. 评估 runner、数据集与 demo cases 仅占位，尚未实现自动评估。

## 后续风险

- RAG chunk 粒度需要结合真实课程材料迭代。
- Evidence Check 阈值需要通过评估集校准。
- MCP 工具调用的错误分类、超时、重试和降级策略需要在真实链路中验证。
- 前端 trace 展示需要避免暴露敏感输入、完整 prompt 或完整模型输出。
