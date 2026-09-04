# AI 学习伙伴（AI Agent 课程版）

> 一句话愿景：**做一个"学什么都陪你到会"的 AI 学习伙伴——它对每一门课都成立;我们从最懂的 AI Agent 课程开始验证。**

面向学生的课程问答学习伙伴 + 面向讲师的教学洞察看板。后端是**领域无关**的 LangGraph 学习引擎 + **课程包**纵切;前端是 React 双角色 SPA（学生 / 讲师）。

- 学生：24 小时在线陪伴式问答（RAG + 引用直达资料）、训练闭环（出题→作答→批改）、项目陪练（立项向导 + 个性化清单）、个人画像。
- 讲师：教学洞察看板（知识点掌握矩阵、掌握度排行、里程碑漏斗）、掌握度人工修正。

## 架构基因：学习引擎 + 课程包

```
学习引擎 (Learning Engine)   ← 领域无关、可复用
  陪伴 · 学习者档案 · 训练闭环 · 项目闭环 · 教学洞察
        │ 加载
课程包 (Course Pack)         ← 领域特定、可插拔
  资料/知识库 · 知识点体系(taxonomy) · Rubric · 结课项目
        ▲
  第一个课程包 = AI Agent 课程 (LangChain / LangGraph / MCP / RAG)
```

**铁律**：`scaffold/apps/api/app/engine/**` 不得出现任何课程特定硬编码;课程内容一律经 `CoursePack`（`data/course_packs/<id>/`）数据注入。加新课 = 放新目录,引擎零改动。详见 `docs/VISION.md`、`AGENTS.md`、`docs/adr/`。

## 技术栈

- **后端**：Python 3.11、FastAPI、LangGraph（真 StateGraph 编排）、SQLModel（SQLite 业务库）、ChromaDB（向量库）、火山方舟 Ark（LLM `/chat/completions` + doubao 多模态 embedding `/embeddings/multimodal`）。
- **前端**：React 19 + Vite + TS、Tailwind v4、shadcn/ui + Radix、Recharts、Phosphor 图标。
- **鉴权**：轻量自签 token（bcrypt + stdlib HMAC,非 JWT 库),角色随 token 携带(学生 `stu_` / 讲师 `tea_`)。

## 本地开发

前置：`python3.11`、`uv`、`pnpm 11`、`node`。运行 `./init.sh` 打印环境检查与全部校验命令（只打印,不改环境）。

```bash
# 后端(Python 3.11,用 uv)
cd scaffold/apps/api
uv venv --python 3.11 .venv
uv pip install -e '.[dev]'
# Ark 配置:仓库根 .env 与 scaffold/apps/api/.env(EMBEDDING_DIM 须与已建 Chroma 索引一致,本机 2048)

# 前端(pnpm + Node)
cd scaffold
pnpm --dir apps/web install
```

两个服务分别起（前端 dev 经 Vite proxy 把 `/api` 转发到 `:8000`）：

```bash
# 后端 :8000
cd scaffold/apps/api && .venv/bin/uvicorn app.main:app --port 8000
# 前端 :5173(另开终端)
cd scaffold && pnpm --dir apps/web run dev
```

浏览器打开 http://localhost:5173 。默认学生视图;讲师账号登录后可见教学洞察。

## 环境变量

配置项由后端 `app/core/config.py` 用 pydantic-settings 读取,来源是仓库根 `.env` 与 `scaffold/apps/api/.env`(均已 gitignore)。**复制 `.env.example` 为 `.env` 后按需填值**;未设置的项一律用代码默认值。本地开发把 `APP_ENV=local`、鉴权用 dev 占位即可直接跑。

| 变量 | 默认值 | 说明 |
|---|---|---|
| `APP_ENV` | `local` | `local` / `production`;生产时 dev 占位密钥会 **fail-fast 拒绝启动** |
| `AUTH_TOKEN_SECRET` | `dev-insecure-secret-change-me` | 自签 token 签名密钥(非 JWT),生产必须覆盖 |
| `AUTH_TEACHER_INVITE_CODE` | `dev-teacher-invite` | **讲师注册邀请码**,生产必须覆盖 |
| `AUTH_TOKEN_TTL_HOURS` | `168` | token 有效期(小时) |
| `LLM_PROVIDER` | `mock` | `openai_compatible` 走 Ark,否则用 mock(无需 key) |
| `LLM_API_KEY` / `LLM_MODEL` | 空 | Ark key 与推理接入点 `ep-xxxx` |
| `EMBEDDING_PROVIDER` | `mock` | `ark_multimodal` 走 Ark 多模态,否则 mock |
| `EMBEDDING_API_KEY` / `EMBEDDING_MODEL` | 空 | Ark key 与 embedding 接入点 `ep-xxxx` |
| `EMBEDDING_DIM` | `768` | ⚠️ 必须与已建 Chroma 索引一致(本项目 **2048**) |
| `DATABASE_URL` / `BUSINESS_DB_URL` | sqlite | 脚手架库 / 业务库(ADR-0005) |
| `CHROMA_PERSIST_DIR` | `data/chroma` | 向量库持久化目录 |
| `CORS_ALLOW_ORIGINS` | 空 | 前后端分离到不同域时填(逗号分隔);同源反代留空 |

完整清单与注释见 `.env.example`。

## 账号与角色

- **无预置账号**:项目不 seed 任何管理员/讲师账号,首个讲师需自行注册。角色仅 `student` / `teacher` 两种(无独立 admin);讲师即管理员,教学洞察与候选审核等接口由后端 `require_teacher` 守卫强制。
- **学生**:直接注册,无需邀请码。
- **讲师**:注册时必须带 `AUTH_TEACHER_INVITE_CODE`(本地默认 `dev-teacher-invite`)。示例(后端已在 `:8000` 运行):

```bash
curl -s -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"teacher1","password":"secret123","role":"teacher","invite_code":"dev-teacher-invite"}'
```

返回含 `token`,前端登录后即拥有讲师视图。用户名 2-32 位字母/数字/下划线/中文,密码至少 6 位。要改邀请码,在 `.env` 设 `AUTH_TEACHER_INVITE_CODE=你的码` 并重启后端。

## 验证命令（声明完成前必须真实运行）

```bash
# 后端:分层单测 + eval 门禁
cd scaffold/apps/api
.venv/bin/pytest -q                                          # 期望 164 passed, 1 skipped
.venv/bin/python ../../evals/runner/qa_quality_runner.py     # 期望 4/4 cases passed

# 前端:三关全绿、零告警
cd scaffold
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run lint
pnpm --dir apps/web run build
```

1 skip = 真实 Ark embedding 冒烟（需先 export 根 `.env`）。

## 容器化部署（ADR-0010）

前端 nginx 同源反代 `/api` 到后端,默认**免 CORS**。

```bash
cp deploy/.env.deploy.example deploy/.env.deploy   # 填 Ark key + 生产密钥
docker compose up --build
# 浏览器打开 http://localhost:8080
```

- `deploy/api.Dockerfile` / `deploy/web.Dockerfile` / `deploy/nginx.conf`：镜像与反代配置。
- `docker-compose.yml`：api（含 `/healthz` 健康检查）+ web；命名卷 `tutor-data` 持久化业务库/向量索引。
- ⚠️ **生产必须覆盖** `AUTH_TOKEN_SECRET` 与 `AUTH_TEACHER_INVITE_CODE`——`APP_ENV=production` 时若仍是 dev 占位,后端**启动即失败**（fail-fast）。
- 前后端分离到不同域时,给后端设 `CORS_ALLOW_ORIGINS`（逗号分隔）启用 CORS。
- 生产日志为**单行 JSON 结构化输出**（`APP_ENV=production` 自动切换,便于采集）。

## 文档地图

| 文件 | 内容 |
|---|---|
| `AGENTS.md` | agent 协作说明 + 铁律 + 完成定义（**先读**） |
| `.env.example` | 环境变量模板（复制为 `.env` 填值） |
| `docs/VISION.md` | 产品愿景（北极星） |
| `docs/DESIGN.md` | 总技术方案 |
| `docs/FRONTEND.md` | 前端方案 + 质感纪律 |
| `docs/PRD.md` | 产品需求 |
| `docs/teaching/` | 教学文档（项目介绍 / 模块设计详解 / 面试要点） |
| `CONTEXT.md` | 术语表 |
| `docs/adr/` | 架构决策记录（ADR-0001~0010） |
| `feature_list.json` | feature 状态 + 完成证据 |
| `progress.md` / `session-handoff.md` | 进度日志 / 会话交接 |

## 当前状态

MVP 已端到端验证,正进行生产化改造（三梯队）。已完成：后端学习引擎（问答/训练/项目/洞察）+ 课程包纵切、React 双角色 SPA、学生/讲师登录鉴权、容器化部署 + CORS 策略 + 生产配置固化。详见 `progress.md`。
