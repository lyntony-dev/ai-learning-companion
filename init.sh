#!/bin/bash
set -e

echo "=== AI 学习伙伴 — 校验 (后端 Python 栈 + 前端 React) ==="

API_DIR="scaffold/apps/api"
WEB_DIR="apps/web"

# 1. Python 版本
echo "--- Python ---"
python3 --version || { echo "缺少 python3"; exit 1; }

# 2. 依赖(用 uv 建 py3.11 venv;系统 python 为 3.9,项目要求 >=3.11)
echo "--- 依赖检查 (${API_DIR}) ---"
if [ -f "${API_DIR}/pyproject.toml" ]; then
  if [ -x "${API_DIR}/.venv/bin/python" ]; then
    echo ".venv 已就绪: ${API_DIR}/.venv"
  elif command -v uv >/dev/null 2>&1; then
    echo "建环境: (cd ${API_DIR} && uv venv --python 3.11 .venv && uv pip install -e '.[dev]')"
  else
    echo "uv 未安装;手动: python3.11 -m venv ${API_DIR}/.venv && ${API_DIR}/.venv/bin/pip install -e '${API_DIR}[dev]'"
  fi
else
  echo "警告:未找到 ${API_DIR}/pyproject.toml"
fi

# 3. .env(Ark 配置,不进 git)
echo "--- 配置 ---"
if [ -f ".env" ]; then
  echo ".env 存在(应含 Ark base_url / key / LLM / embedding endpoint;密钥不打印)"
else
  echo "警告:缺少 .env — 参考 docs/DESIGN.md §7 配置 Ark"
fi

# 4. 测试(分层单测 + 纵切集成 + eval 门禁,在 api 目录跑)
echo "--- 测试 ---"
if [ -d "${API_DIR}/tests" ]; then
  echo "运行: (cd ${API_DIR} && .venv/bin/pytest -q)"
  echo "  覆盖:配置/持久化/课程包/摄取/主图/子图(问答·训练·项目)/纵切/教学洞察/eval 门禁"
  echo "eval 独立跑: (cd ${API_DIR} && .venv/bin/python ../../evals/runner/qa_quality_runner.py)"
  echo "真实 Ark 冒烟(需先 export 根 .env): (cd ${API_DIR} && set -a && . ../../../.env && set +a && .venv/bin/pytest -q -k smoke)"
else
  echo "警告:未找到 ${API_DIR}/tests"
fi

# 5. 前端(React + pnpm;dev 经 Vite proxy 转发 /api → :8000)
echo "--- 前端 (scaffold/${WEB_DIR}) ---"
if [ -f "scaffold/${WEB_DIR}/package.json" ]; then
  if command -v pnpm >/dev/null 2>&1; then
    if [ -d "scaffold/${WEB_DIR}/node_modules" ]; then
      echo "node_modules 已就绪"
    else
      echo "装依赖: (cd scaffold && pnpm --dir ${WEB_DIR} install)   # .npmrc 已配 esbuild 构建豁免"
    fi
    echo "三关校验: (cd scaffold && pnpm --dir ${WEB_DIR} run typecheck && pnpm --dir ${WEB_DIR} run lint && pnpm --dir ${WEB_DIR} run build)"
  else
    echo "警告:pnpm 未安装(前端需 pnpm 11)"
  fi
else
  echo "警告:未找到 scaffold/${WEB_DIR}/package.json"
fi

echo ""
echo "=== 校验命令已列出 ==="
echo ""
echo "本地开发运行(两个终端):"
echo "  后端 :8000  (cd ${API_DIR} && .venv/bin/uvicorn app.main:app --port 8000)"
echo "  前端 :5173  (cd scaffold && pnpm --dir ${WEB_DIR} run dev)  → http://localhost:5173"
echo ""
echo "容器化部署(ADR-0010,nginx 同源反代免 CORS):"
echo "  cp deploy/.env.deploy.example deploy/.env.deploy   # 填 Ark key + 生产密钥"
echo "  docker compose up --build   → http://localhost:8080"
echo "  ⚠️ 生产(APP_ENV=production)必须覆盖 AUTH_TOKEN_SECRET / AUTH_TEACHER_INVITE_CODE,否则启动失败"
echo ""
echo "下一步:"
echo "1. 读 docs/DESIGN.md(总方案)+ docs/FRONTEND.md(前端方案+质感纪律)+ CONTEXT.md(术语)+ docs/adr/(决策)"
echo "2. 读 feature_list.json,按依赖顺序挑一个 not-started 的 feature"
echo "3. 只实现那一个 feature,遵守引擎/课程包解耦铁律 + 前端质感纪律"
echo "4. 声明完成前:后端跑 pytest + eval,前端跑 typecheck/lint/build,把证据写回 feature_list.json"
