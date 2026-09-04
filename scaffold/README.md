# AI Agent 课程助教系统

基于 LangGraph、MCP 与 RAG 的课程助教 MVP-B Monorepo。

## PR 1 范围

本 PR 只建立工程骨架与可演示静态界面，不实现真实业务链路。

已包含：

1. FastAPI 后端骨架：`/healthz`、`/api/version`、配置加载、请求日志中间件、基础测试。
2. Course Search MCP mock server：`list_courses`、`search_course_material`、`get_course_chunk` 的 schema、mock 工具与测试。
3. React + Vite 前端静态三栏 UI：左侧课程/会话、中间 Chat、右侧 Sources 与 Agent Trace。
4. 根目录工程文件：`.env.example`、`.gitignore`、`docker-compose.yml`、`Makefile`、基础 docs。

## 目录结构

- `apps/api`：FastAPI API 服务。
- `apps/mcp_servers/course_search`：Course Search MCP mock server。
- `apps/web`：React 前端。
- `packages/shared`：跨端共享 schema 与常量占位。
- `data/course_materials`：课程材料导入目录占位。
- `data/chroma`：向量索引持久化目录占位。
- `docs`：实现清单、限制说明、演示用例。
- `evals`：后续评估数据集与 runner 占位。

## 本地命令

```bash
make check
make test-api
make test-mcp
make web-typecheck
```

> PR 1 不启动任何网络监听进程；`docker-compose.yml` 中服务仅放入 `manual` profile，供后续手动开发使用。

## 环境变量

复制 `.env.example` 为 `.env` 后按需调整。默认使用 mock provider，不需要真实 LLM 或 Embedding 密钥。

## 后续 PR

1. PR 2：配置、SQLite 数据模型、trace/eval 基础表。
2. PR 3：课程材料 ingestion CLI。
3. PR 4：Course Search MCP Server 真实检索实现。
4. PR 5：LangGraph 主链路。
5. PR 6：FastAPI 核心接口。
6. PR 7：前端真实 API 接入与评估入口。
