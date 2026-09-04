# ADR-0010：容器化部署与 CORS 策略——nginx 同源反代优先

- 状态：已接受
- 日期：2026-07-26

## 背景

MVP 此前只有本地双进程开发路径(uvicorn:8000 + Vite dev:5173,靠 Vite proxy 同源转发 `/api`),缺少可交付的生产/演示部署方式:

- 根目录仅有 PR1 时代的 `scaffold/docker-compose.yml` 占位(`manual` profile、指向 `python -m app.main`、用 `.env.example`),既不能真正起服务,也没有前端镜像。
- `app/main.py` **无 CORS 中间件**;一旦前后端拆到不同域,浏览器会拦截跨域请求。
- 关键路径耦合:`course_pack/loader.py` 用 `parents[5]` 定位**仓库根** `data/course_packs`,而业务库/Chroma 相对 `apps/api` 工作目录——镜像必须保留同样的目录层级。

## 决策

- **前端 nginx 同源反代优先**:web 镜像用 nginx 提供 React 构建产物,并把 `/api` 反代到 `api:8000`。前后端对浏览器同源,**默认不需要 CORS**。这是最简单、最少出错的部署形态。
- **CORS 作为可选开关**:`app/main.py` 增加 `CORSMiddleware`,**仅当** `CORS_ALLOW_ORIGINS`(逗号分隔)非空时启用。默认留空=不加任何 CORS 头,零行为变化。为前后端分离到不同域的部署留后路。
- **构建上下文=仓库根**:两个 Dockerfile(`deploy/api.Dockerfile`、`deploy/web.Dockerfile`)都以仓库根为 context,容器内保留 `/app/scaffold/apps/api` 层级,使 `parents[5]` 正确解析到 `/app/data/course_packs`。
- **数据持久化**:业务库 SQLite + Chroma 索引落在 `api` 容器的 `/app/scaffold/apps/api/data`,由 compose 命名卷 `tutor-data` 持久化,容器重建不丢学习数据。
- **依赖管理对齐本地**:api 镜像用 `uv`(与本地开发一致);web 镜像用 `pnpm --frozen-lockfile`。
- **密钥不进镜像**:`.dockerignore` 排除所有 `.env*`(仅 `deploy/.env.deploy.example` 例外);运行期密钥经 compose `env_file: deploy/.env.deploy` 注入。

候选:A 前端也用 Node 起 `vite preview`(多一个 Node 进程 + 需应用层解决跨域,弃用);B nginx 静态 + 同源反代(采纳,最省心);C 后端直接 `StaticFiles` 挂前端产物(把前端构建塞进 Python 镜像,职责耦合,弃用)。

## 影响

- **正面**:一条 `docker compose up --build` 即可起完整应用(http://localhost:8080);默认同源免 CORS;数据卷持久化;镜像不含密钥。
- **代价/风险**:
  - SQLite 单文件适合单实例 demo;多副本水平扩展需换 Postgres + 外置向量库(V2)。
  - 课程包烘焙进镜像,换课需重建镜像或改挂载卷;符合「加新课=放新目录」但生产换课节奏偏重。
  - 启用 CORS 时 `allow_credentials=True` 要求 `allow_origins` 为具体域名(不能用 `*`),已在配置文档中说明。

## 验证

- 后端 `pytest`:`test_cors.py` 覆盖来源解析、默认关闭(无 `access-control-allow-origin` 头)、显式配置后放行指定来源。全量套件通过。
- 部署产物为静态审阅(本机未必有 Docker daemon):Dockerfile/compose/nginx 配置与仓库实际路径、端口、卷、健康检查逐项对齐;`.dockerignore` 防止密钥与大文件进镜像。
