# AI Agent 学习伙伴 —— 后端镜像(FastAPI + LangGraph 学习引擎)
#
# 构建上下文必须是仓库根:course_pack/loader.py 用 parents[5] 定位
# 仓库根的 data/course_packs,镜像内需保留同样的相对层级。
#   docker build -f deploy/api.Dockerfile -t course-tutor-api .
FROM python:3.11-slim AS base

# uv:与本地开发一致的依赖管理
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

# 层级须与仓库一致,使 parents[5] 在容器内解析到 /app
WORKDIR /app/scaffold/apps/api

# 先装依赖(利用层缓存):仅 pyproject 变化才重装
COPY scaffold/apps/api/pyproject.toml ./
RUN uv venv --python 3.11 .venv \
    && uv pip install --python .venv/bin/python -e '.'

# 拷贝应用代码与课程包(course_packs 在仓库根,parents[5] 定位)
COPY scaffold/apps/api/app ./app
COPY data/course_packs /app/data/course_packs

# 运行期业务库/向量索引落在此(compose 挂 volume 持久化)
RUN mkdir -p /app/scaffold/apps/api/data

ENV PATH="/app/scaffold/apps/api/.venv/bin:${PATH}"

EXPOSE 8000

# 生产用多 worker;学习引擎为无状态请求,SQLite 单文件适合单实例 demo
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
