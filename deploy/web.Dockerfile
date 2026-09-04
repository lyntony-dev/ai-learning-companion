# AI Agent 学习伙伴 —— 前端镜像(React 构建产物 + nginx 静态服务/反代)
#
# 构建上下文为仓库根:
#   docker build -f deploy/web.Dockerfile -t course-tutor-web .
FROM node:20-slim AS build

# pnpm 与本地锁版本一致(scaffold/package.json 里 packageManager 或 corepack)
RUN corepack enable

WORKDIR /app

# workspace 元信息 + 锁文件先拷贝,利用层缓存
COPY scaffold/pnpm-workspace.yaml scaffold/pnpm-lock.yaml scaffold/.npmrc* ./
COPY scaffold/apps/web/package.json ./apps/web/package.json
RUN pnpm --dir apps/web install --frozen-lockfile || pnpm --dir apps/web install

# 拷贝源码并构建(前端 BASE='/api',由 nginx 同源反代)
COPY scaffold/apps/web ./apps/web
RUN pnpm --dir apps/web run build

# --- 运行期:nginx 提供静态资源 + /api 反代到后端 ---
FROM nginx:1.27-alpine AS runtime

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
