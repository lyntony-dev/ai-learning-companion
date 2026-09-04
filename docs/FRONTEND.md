# FRONTEND — AI 学习伙伴 前端实现方案

> 本文是**前端技术实现方案**。技术总方案见 `docs/DESIGN.md`,前端关键决策见 `docs/adr/0007-frontend-stack-dual-role.md`,愿景见 `docs/VISION.md`,术语见 `CONTEXT.md`。
> 状态:**已实现并端到端验证**(2026-07-16)。冲突时以 ADR-0007 > 本文 > 脚手架现状为序。
> 质感纪律来自 taste-skill(反 AI 套路前端框架):采纳其**通用反套路纪律**,不套用其**营销页专属规则**(判定见 ADR-0007)。
>
> 落地记录:PR1~5 已在 `scaffold/apps/web` 实现,`typecheck`/`lint`/`build` 三关通过;起后端 + 前端跑通问答(真实 Ark 回答 + 引用 + 9 节点 trace)、洞察看板、掌握度修正(含 422/404 路径)。真实模型验证需 `apps/api/.env` 配置 Ark(embedding 维度须与已建索引一致,本机为 2048)。

## 0. 本文回答什么

如何把现有 `apps/web`(React19+Vite+原生 CSS 的三栏 mock UI,`api/client.ts` 直接 throw)改造成**可点、接真实后端**的双角色产品:学生端问答 + 讲师端洞察看板。仅接已就绪后端(`/api/chat`、`/api/insights/*`);训练(E)/ 项目(F)/ 真实鉴权 / 流式输出归**下一迭代**,本轮只留信息架构占位。

## 1. 范围(承接 ADR-0007,已锁)

| 面 | 本轮 | 说明 |
|---|---|---|
| 学生端问答页 | ✅ 接真实 `/api/chat` | 三栏:会话 / 对话 / 来源&轨迹 |
| 讲师端洞察看板 | ✅ 接真实 `/api/insights/*` | 单页钻取 + inline 掌握度修正 |
| 角色切换 | ✅ 顶部切换器(demo,无登录) | 诚实标注无鉴权 |
| 训练(E)/ 项目(F)入口 | ⬜ 导航留入口 + empty state | 标"下一迭代上线",无假数据假按钮 |
| 真实鉴权登录 | ❌ 下一迭代 | 本轮 demo 角色切换 |
| 流式输出 / 逐字打字 | ❌ 下一迭代 | 后端同步无流,不假装 |

## 2. 技术栈(ADR-0007 §技术栈,钉版本)

| 类别 | 选型 | 备注 |
|---|---|---|
| 框架 | React 19 + Vite + TypeScript | 沿用脚手架,不迁 Next(纯内部产品无 SSR/SEO) |
| 样式 | Tailwind v4(`@tailwindcss/vite`) | 替换现有原生 CSS |
| 组件 | shadcn/ui(自拥有)+ Radix 原语 | taste-skill 点名的产品 UI 方案 |
| 动效 | Motion(`motion/react`) | 连续值用 `useMotionValue` 非 `useState` |
| 图表 | Recharts | 覆写默认配色/网格,套锁定 accent |
| 图标 | Phosphor(单库) | 禁手搓 SVG、禁混库、劝退 lucide |
| 数据请求 | fetch 封装(现 `api/client.ts` 重写)+ 局部 state | **MVP 锁定轻量方案**,不引 TanStack Query,留接口 |

**依赖钉版本**:现脚手架全 `latest` 不可复现,本轮全部改固定版本号(锁 `pnpm-lock.yaml`)。

## 3. 视觉语言(taste-skill 三档位,ADR-0007 §视觉)

- **档位**:`DESIGN_VARIANCE: 5` / `MOTION_INTENSITY: 3` / `VISUAL_DENSITY: 6`。
- **Design Read**:学习型双角色产品 UI(对话工具 + 数据看板),Linear/Notion 式冷静克制。
- **配色锁**:中性底(Zinc/Slate)+ **单一 accent 全站锁定**;深浅双主题,整页锁一个主题不中途翻转。
- **字体**:Geist(禁 Inter 默认、禁 serif 默认)。
- **圆角锁**:单一圆角尺度全站锁定。
- **动效清单**(只保留有意义的):消息进入淡入上移、trace 节点展开、洞察数字滚动(`useMotionValue`)、侧滑抽屉。禁 scroll 劫持 / marquee / GSAP-for-show。`MOTION_INTENSITY>3` 的动效包 `prefers-reduced-motion` 回退。
- **文案纪律**:禁 em-dash;按钮/表单文本满足 WCAG AA 对比度。

## 4. 路由与页面结构

```
/                       → 重定向到 /student
/student                → 学生端问答页(三栏)
/teacher                → 讲师端洞察看板(单页钻取)
/training               → empty state「下一迭代上线」(导航占位)
/capstone               → empty state「下一迭代上线」(导航占位)
```

顶部 **RoleSwitcher**(学生 / 讲师)= demo 模式身份,切换即换路由与视图,标注"演示模式 · 无鉴权"。

### 4.1 学生问答页 `/student`(三栏)

```
┌───────────┬──────────────────────────┬─────────────────────┐
│ 会话列表   │  对话区                    │  右侧 Tab            │
│ (左)      │  (中)                     │  引用来源 / Agent Trace│
│           │                          │                     │
│ + 新会话   │  [消息流]                  │ [Tab: 来源]          │
│ 会话1     │   用户提问                  │  SourceCard [1]      │
│ 会话2 ←选中│   助手回答 + 角标[1][2]     │  SourceCard [2]      │
│ ...       │                          │ [Tab: Trace]         │
│           │  ────────────            │  retrieve ✓          │
│           │  [输入框 + 发送]           │  answer ✓            │
│           │                          │  review ✓            │
└───────────┴──────────────────────────┴─────────────────────┘
```

- 回答正文中的引用角标 `[n]` 可点击 → 联动切到右侧「来源」Tab 并高亮/滚动到对应 `SourceCard`(用 `citation_id` 关联)。
- 回答 `status === "insufficient"`(拒答)时,正文展示诚实拒答,不显示编造页码;来源 Tab 空态。
- 等待期(`/api/chat` 真实十几秒)→ **骨架屏 + 分阶段节点提示**(见 §6)。

### 4.2 讲师洞察看板 `/teacher`(单页钻取)

```
┌────────────────────────────────────────────────────────────┐
│ 概览指标条:学员数 / 平均掌握 / 薄弱点数 / 里程碑通过率          │
├────────────────────────────────────────────────────────────┤
│ 知识点掌握度矩阵(topics[]:known/fuzzy/unknown 堆叠条)        │
├────────────────────────────────────────────────────────────┤
│ 薄弱点排行(weak_ranking[])   │  里程碑漏斗(milestones[])     │
├────────────────────────────────────────────────────────────┤
│ 学员列表 → 点击行 → 侧滑抽屉:个体档案(masteries[])           │
│                              inline 修正掌握度(known/fuzzy/  │
│                              unknown)→ POST mastery-corrections│
└────────────────────────────────────────────────────────────┘
```

- 顶层用 `GET /api/insights/courses/{course_pack_id}`(默认 `ai_agent`)。
- 点学员行 → `GET .../learners/{learner_id}` 填充侧滑抽屉。
- inline 修正 → `POST .../mastery-corrections`,乐观更新 + 失败回滚;`updated_by` 必填(空 → 后端 422,前端先校验)。修正后 `source` 变 `instructor_corrected`,UI 标"讲师已修正"。

## 5. 组件与文件清单(在现有 `apps/web/src` 上演进)

```
src/
  main.tsx                        # 挂 Router + ThemeProvider
  App.tsx                         # 【重写】去 mockData,改路由外壳
  routes/                         # 【新】
    student.tsx                   # 学生问答页
    teacher.tsx                   # 讲师洞察看板
    training.tsx capstone.tsx     # empty state 占位
  components/
    layout/
      AppShell.tsx                # 【改】顶栏 + RoleSwitcher + 主题切换
      RoleSwitcher.tsx            # 【新】demo 角色切换
    chat/
      ConversationList.tsx        # 【新】左栏会话列表(GET /conversations)
      MessageStream.tsx           # 【改】消息流,角标[n]可点
      ChatMessage.tsx ChatInput.tsx  # 【改】接真实提交
      Citation.tsx                # 【新】[n] 角标联动
    sources/
      SourcesPanel.tsx SourceCard.tsx  # 【改】接 citations[]
    trace/
      TracePanel.tsx TraceTimelineItem.tsx  # 【改】接 trace[]/分阶段提示
    insights/                     # 【新】
      OverviewBar.tsx             # 概览指标(数字滚动)
      MasteryMatrix.tsx           # 掌握度堆叠条(Recharts)
      WeakRanking.tsx             # 薄弱排行
      MilestoneFunnel.tsx         # 里程碑漏斗(Recharts)
      LearnerDrawer.tsx           # 侧滑个体档案 + inline 修正
    ui/                           # 【新】shadcn/ui 生成的自拥有组件
    feedback/                     # 【新】
      Skeleton*.tsx               # 匹配最终布局的骨架屏
      EmptyState.tsx ErrorState.tsx
  api/
    client.ts                     # 【重写】去 throw,真实 fetch 封装
    chat.ts insights.ts           # 【新】按契约的类型化调用
  types/                          # 【改】对齐后端 schema(见 §7)
    chat.ts source.ts trace.ts insights.ts
  lib/theme.ts                    # 【新】主题锁 / prefers-reduced-motion
  styles/globals.css              # 【改】Tailwind v4 + 设计 token
  mocks/demoData.ts               # 【删】真实接口后移除
```

## 6. 状态与真实性(ADR-0007 §状态)

每个数据面必须实现四态:

| 态 | 学生问答 | 讲师看板 |
|---|---|---|
| loading | 骨架屏(匹配三栏最终布局)+ 分阶段节点提示 retrieve→answer→review | 卡片骨架屏(禁通用 spinner) |
| empty | 无会话引导 / 拒答空来源 | 课程无数据引导 |
| error | Ark/网络报错可读提示 + 重试 | 同左 |
| success | 正常渲染 | 正常渲染 |

- **分阶段提示**:`/api/chat` 同步返回全部 `trace[]`,但等待期先展示"引擎工作中"的节点占位动画(retrieve→answer→review),返回后一次性填真实 trace。把十几秒延迟转成"看得见引擎在工作"。
- **不做假流式**:后端不支持流,前端不逐字打字;真实流式归下一迭代。

## 7. API 契约映射(仅接已就绪后端)

Base:后端路由前缀 `/api`。Vite dev proxy 转发 `/api` → 后端。

### 7.1 学生问答

- `POST /api/chat`
  - 请求 `ChatRequest`:`{ question, conversation_id?, user_id="demo_user", course_ids=[], top_k=5 }`(`top_k` 1–20)。本轮**不传** `task_type`/`learner_answer`(后端未暴露,固定走 rag_answer)。
  - 响应 `ChatResponse`:`{ conversation_id, trace_id, answer, status, citations[], trace[] }`。
    - `status`:`"insufficient"`(拒答)| 证据等级 `"strong"`/`"weak"`。
    - `Citation`:`{ citation_id, chunk_id, course_id, course_name, section, source_path, slide_no }` → `SourceCard` 与角标 `[n]` 关联键 = `citation_id`。
    - `AgentTraceEvent`:`{ node_name, status, input_summary, output_summary, metadata }` → `TraceTimelineItem`。
- `GET /api/conversations` → 左栏会话列表。
- `GET /api/conversations/{id}/messages` → 选中会话历史。
- `GET /api/conversations/{id}/trace`(或 by trace_id)→ 轨迹回看(按后端实际)。

### 7.2 讲师洞察

- `GET /api/insights/courses/{course_pack_id}`(默认 `ai_agent`)→ `CourseInsightsResponse`:
  `{ course_pack_id, learner_count, topics[], weak_ranking[], milestones[] }`
  - `TopicInsight`:`{ topic_id, name, course_id, known, fuzzy, unknown, attempts, avg_score:float|null }`。
  - `MilestoneInsight`:`{ milestone, not_started, in_progress, passed }`。
- `GET /api/insights/courses/{course_pack_id}/learners/{learner_id}` → `LearnerProfileResponse`:
  `{ learner_id, course_pack_id, masteries[] }`,`MasteryEntry{ topic_id, name, level, source, updated_by }`。
- `POST /api/insights/courses/{course_pack_id}/mastery-corrections`:
  请求 `{ learner_id, topic_id, level, updated_by }`(`level` ∈ known/fuzzy/unknown;`updated_by` 必填)。
  响应 `{ learner_id, topic_id, level, source, updated_by }`(`source`→`instructor_corrected`)。
  错误:空 `updated_by` 或超出 taxonomy 的 `topic_id` → 422;课程包不存在 → 404。前端做前置校验 + 乐观更新回滚。

**枚举**:`MasteryLevel = known | fuzzy | unknown`;`MasterySource = system_inferred | instructor_corrected`。前端 `types/insights.ts` 与后端 schema 逐字段对齐。

> 数据请求层 **MVP 锁定轻量方案**:`api/client.ts`(真实 fetch 封装)+ 组件局部 state,不引 TanStack Query,但按面拆分 `chat.ts`/`insights.ts` 留出后续替换接口。

## 8. 下一迭代边界(明确不做)

- 训练(E)/ 项目(F):后端无 HTTP 端点 → 仅留导航入口 + empty state。
- 真实鉴权登录:本轮 demo 角色切换器替代。
- 流式输出 / 逐字打字:后端同步无流。
- 真实产出物/代码判题、自适应路径、后台触达:承接 DESIGN.md 扩展点。

## 9. 落地步骤(建议 PR 切分)

1. **基座**:钉依赖版本、接 Tailwind v4 + shadcn/ui + Phosphor + 主题锁 + 路由 + AppShell/RoleSwitcher;删 mockData。
2. **数据层**:重写 `api/client.ts` 为真实 fetch,`chat.ts`/`insights.ts` 类型化调用,`types/*` 对齐后端;Vite dev proxy。
3. **学生问答页**:三栏、会话列表、消息流、角标联动、来源/Trace Tab、四态 + 骨架屏分阶段提示,接 `/api/chat`。
4. **讲师看板**:概览/矩阵/排行/漏斗(Recharts 覆写)、侧滑档案 + inline 修正,接 `/api/insights/*`。
5. **占位与收尾**:training/capstone empty state、深浅主题、`prefers-reduced-motion`、对比度与 em-dash 纪律核查。

## 10. 验证策略

- **构建/类型**:`pnpm build`(`tsc --noEmit && vite build`)、`pnpm typecheck`、`pnpm lint` 零告警。
- **契约对齐**:`types/*` 字段与后端 schema 逐字段核对(§7);修正流 422/404 路径手测。
- **端到端手测**:真实起后端 + 前端,跑通「提问→拒答/正常→角标联动→trace」与「看板钻取→侧滑→修正落库」。
- **质感核查(taste-skill 清单)**:配色单 accent 锁定、单圆角、Geist、Phosphor 单库、无 em-dash、AA 对比度、动效有据且带 reduced-motion 回退、四态齐全、无通用 spinner。
