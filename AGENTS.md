# AGENTS.md

AI 学习伙伴（AI Agent 课程版）的 agent 协作说明。**先读本文,再动代码。**

产品:面向学生的课程问答学习伙伴 + 面向讲师的教学洞察看板。后端是领域无关的 LangGraph 学习引擎 + 课程包纵切;前端是 React 双角色 SPA。当前状态:**MVP 已完成并端到端验证**(后端 feat-001~010 + 前端 FE-001~004)。

## 启动流程 / Startup Workflow(每次会话开始)

Before writing code:

1. `pwd` 确认工作目录为仓库根 `ai-agent-course-tutor`。
2. 读完本文件。
3. 读文档:`docs/DESIGN.md`(总方案)、`docs/FRONTEND.md`(前端方案+质感纪律)、`CONTEXT.md`(术语)、`docs/adr/`(决策记录)、`docs/VISION.md`(愿景)。
4. 运行 `./init.sh` 打印环境与校验命令(它只打印命令,不自动改环境)。
5. 读 `feature_list.json` 看 feature 状态,读 `progress.md` / `session-handoff.md` 接续上下文。

基线校验若失败,先修基线再加新范围。

## 铁律(不可违反)

- **引擎领域无关**:`scaffold/apps/api/app/engine/**` 不得出现任何课程特定内容(课程名、知识点、题目、里程碑硬编码)。课程特定内容一律经 `CoursePack` 数据注入(约定目录 `data/course_packs/<id>/`,见 ADR-0002/0006)。加新课 = 放新目录,引擎零改动。
- **诚实**:证据不足要拒答,不编造引用/页码;后端无流式就不做假流式;后端没有的接口不在前端造假数据假按钮(标"下一迭代")。
- **不提交密钥**:`.env`(仓库根与 `scaffold/apps/api/.env`)含 Ark key,已 gitignore,永不提交。
- **一次一个 feature(One feature at a time)**:从 `feature_list.json` 挑一个未完成项;完成前跑校验并回写证据。
- **不越范围(Stay in scope)**:不改与当前 feature 无关的文件;后端没有的接口不在前端造假。

## 环境初始化

**后端(Python 3.11,用 uv)**
```bash
cd scaffold/apps/api
uv venv --python 3.11 .venv
uv pip install -e '.[dev]'
# Ark 配置:仓库根 .env 与 apps/api/.env(embedding 维度须与已建 Chroma 索引一致,本机为 2048)
```

**前端(pnpm 11 + Node)**
```bash
cd scaffold                      # .npmrc/pnpm-lock 在此;esbuild 构建豁免已配好
pnpm --dir apps/web install
```

## 本地开发运行

两个服务分别起(前端 dev 经 Vite proxy 把 `/api` 转发到 `:8000`):
```bash
# 后端 :8000
cd scaffold/apps/api && .venv/bin/uvicorn app.main:app --port 8000

# 前端 :5173(另开一个终端)
cd scaffold && pnpm --dir apps/web run dev
```
浏览器打开 http://localhost:5173 。默认学生视图,右上角 RoleSwitcher 切讲师(demo 无鉴权)。

## 验证命令(声明完成前必须真实运行)

```bash
# 后端:分层单测 + 纵切 + eval 门禁
cd scaffold/apps/api && .venv/bin/pytest -q          # 期望 68 passed, 1 skipped
.venv/bin/python ../../evals/runner/qa_quality_runner.py   # 期望 4/4 cases passed
# 真实 Ark 冒烟(需先 export 根 .env,否则相关用例 skip):
#   (cd scaffold/apps/api && set -a && . ../../../.env && set +a && .venv/bin/pytest -q -k smoke)

# 前端:三关必须全绿、零告警
cd scaffold && pnpm --dir apps/web run typecheck
pnpm --dir apps/web run lint
pnpm --dir apps/web run build
```
1 skip = 真实 Ark embedding 冒烟(需 export `.env`)。前端暂无单测(`pnpm test` 为占位)。

## 前端设计风格(改前端务必遵守,详见 docs/FRONTEND.md §3/§6)

来自 taste-skill 的通用反套路纪律(不套用其营销页专属规则,判定见 ADR-0007):

- **技术栈钉版本**:React 19 + Vite + TS、Tailwind v4、shadcn/ui(自拥有)+ Radix、Motion、Recharts、Phosphor 单库图标。禁把依赖写成 `latest`。
- **配色**:中性底(Zinc/Slate)+ **单一 accent 全站锁定**;深浅双主题,整页锁一个主题不中途翻转。组件里禁写死 hex,一律用 `var(--color-*)` token。
- **圆角**:单一圆角尺度全站锁定(`var(--radius)`)。
- **图标**:只用 Phosphor,禁手搓 SVG、禁混库。
- **动效**:只保留有意义的动效;连续值用 `useMotionValue` 非 `useState`;`MOTION_INTENSITY>3` 的动效必须带 `prefers-reduced-motion` 回退。禁 scroll 劫持 / marquee / GSAP-for-show。
- **四态**:每个数据面实现 loading(骨架屏匹配最终布局,禁通用 spinner)/ empty / error(可读提示+重试)/ success。
- **文案**:禁 em-dash;按钮/表单满足 WCAG AA 对比度。
- **数据层**:MVP 锁定轻量方案 = `api/client.ts` 真实 fetch + 组件局部 state,不引 TanStack Query;按面拆 `api/{chat,insights,courses}.ts`,类型 `api/types.ts` 与后端 schema 逐字段对齐(snake_case,不做命名转换)。
- **角色感知**:导航/路由按 `useRole()` 过滤与守卫(学生看不到教学洞察)。

## 完成的定义(Definition of Done)

一个 feature 完成,当且仅当全部满足:

- [ ] 目标行为已实现
- [ ] 相关校验真实跑过(后端 pytest + eval;前端 typecheck/lint/build)
- [ ] 证据写回 `feature_list.json` 或 `progress.md`
- [ ] 仓库可从标准启动路径重启(restartable / clean:`./init.sh` + 上面的运行命令)

## 结束会话 / End of Session

Before ending a session:

1. 更新 `progress.md`(当前状态、决策、下一步)。
2. 更新 `feature_list.json`(feature 状态 + 证据)。
3. 记录未解风险/阻塞。
4. 留下干净、可重启的仓库状态。

## 升级/求助

- **架构决策**:先查 `docs/adr/` 与 `docs/DESIGN.md`,无据再问用户。
- **需求不清**:查 `docs/PRD.md` / `docs/VISION.md` / `CONTEXT.md`,无据再问用户。
- **反复测试失败**:更新 `progress.md`,标记人工介入。
- **范围不清**:回读 `feature_list.json` 的依赖与完成定义。
