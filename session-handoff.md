# Session Handoff

## Current Objective

- Goal: 把 MVP 提升为**可发布的完整应用版本**,分三梯队推进。
  - **梯队一(发布下限)**:1) 讲师端鉴权 + 角色权限;2) Dockerfile + docker-compose + CORS 决策;3) 生产密钥/配置固化 + 结构化日志 + README。
  - **梯队二(产品价值)**:4) 画像驱动个性化;5) 讲师审核沉淀流(candidate→approved);6) 我的学习档案聚合页。
  - **梯队三(体验规模)**:7) 流式输出(SSE)、CI、前端单测 + 代码分割、北极星埋点。
- Current status: **三梯队全部完成并验证**。后端 `154 passed / 1 skipped`、eval `4/4`;前端 typecheck/lint/test(8 vitest)/build 四关零告警且构建已分包(无 >500kB 告警)。
- Branch / commit: 非 git 仓库(工作目录直接修改)。

## Completed This Session(梯队三收尾)

- [x] **feat-022 北极星指标 + 代码分割 + 前端单测 + CI**:
  - 后端 `engine/insights/service.py` 加 `north_star_metrics(course_pack_id)`(engagement/honesty/mastery_progress/practice_quality/capstone_funnel);`schemas/insights.py` +6 模型;`routes/insights.py` `GET /api/courses/{id}/metrics`(`require_teacher`,身份取 token 防伪造)。
  - 前端 MetricsPanel + useMetrics + teacher.tsx “北极星指标”Tab。
  - 工程化:`vite.config.ts` `manualChunks`(vendor-charts/markdown/motion)+ App.tsx 路由全 `React.lazy`+Suspense;`vitest.config.ts` + `src/lib/slug.test.ts`(8 条镜像后端);`.github/workflows/ci.yml`(后端 uv+pytest+eval / 前端 pnpm typecheck+lint+test+build,`--frozen-lockfile`)。
  - `tests/test_metrics.py` 6 条。
- [x] **feat-023 诚实节点级流式输出 SSE**:
  - `POST /api/chat/stream`(text/event-stream)经 `graph.stream(stream_mode="values")` 逐节点吐**真实** progress,整图 **review 校验后**吐 final(已校验 answer/citations/trace_id)。
  - **诚实铁律:绝不流式吐未 review 的原始 token**(review 可拒答/降级),故做节点级进度流而非 token 流。
  - `routes/chat.py` 抽出 `_extract_result/_persist_turn/_sse` 与同步 /chat 共用,**同步 /chat 不变、访客零回归**。
  - 前端 `api/chat.ts streamChat`、`useChat.send` 流式优先+失败**优雅回退** postChat、`types/view.ts` +progressNode、`PendingAnswer` 接 activeNode 按真实节点点亮阶段。
  - `tests/test_chat_api.py` +test_chat_stream_emits_progress_then_validated_final。
- [x] harness:`feature_list.json`(feat-022/023)、`progress.md`、本文件。

## Verification Evidence

| Check | Command | Result | Notes |
|---|---|---|---|
| 后端全量单测 | `cd scaffold/apps/api && .venv/bin/pytest -q` | `154 passed, 1 skipped` | +metrics 6 + stream 1;1 skip=真实 Ark embedding 冒烟 |
| eval 质量门禁 | `.venv/bin/python ../../evals/runner/qa_quality_runner.py` | `4/4 cases passed` | 未回归 |
| 前端四关 | `pnpm --dir apps/web run typecheck && lint && test && build` | 全绿零告警 | vitest 8 通过;构建分包无 >500kB 告警 |

## Decisions Made(本轮)

- **流式做节点级而非 token 级**:review 节点在 answer 之后仍可拒答/降级,若逐 token 流会暴露未校验文本,违反诚实铁律。故 SSE 只吐真实节点进度 + 校验后的 final。
- **同步 /chat 保持不变**:流式为新增端点,持久化逻辑抽取共用函数,访客/降级路径零回归;前端流式失败优雅回退同步。
- **代码分割走 manualChunks + React.lazy**:消除单 chunk >500kB 告警,charts/markdown/motion 独立 vendor 包。
- **vitest 而非 jest**:与 Vite 同源,`slug.test.ts` 镜像后端 test_slug 保证前后端 slug 口径一致。

## Blockers / Risks

- 无阻塞。三梯队全部完成。
- ⚠️ **生产部署必须覆盖 `AUTH_TOKEN_SECRET` 与 `AUTH_TEACHER_INVITE_CODE`**(均有 dev 默认值,`APP_ENV=production` 时仍用 dev 占位会 fail-fast)。
- ⚠️ 真实 Ark key 过期需更新根 `.env` 的 LLM_API_KEY/EMBEDDING_API_KEY 才能验证真实 LLM 生成质量与 **SSE 长跑端到端**(本轮流式经 mock provider + FakeRetriever 离线验证)。
- 自签 token 无吊销/刷新,V2 可平滑换 JWT。

## Next Session Startup

1. 读 `AGENTS.md`、`feature_list.json`、`progress.md`。
2. 编辑前跑 `./init.sh`,按其列出命令起服务/跑校验。

## Recommended Next Step(V2 候选,非本轮范围)

- 真实 Ark 长跑压测 + SSE 浏览器端到端验证(node 级进度实时点亮)。
- 班级维度洞察、图片多模态索引、题库沉淀飞轮批量导入。
- E2E(Playwright)与前端组件测试扩面;指标持久化埋点与时间序列趋势。
