# ADR-0007：前端技术栈与双角色产品形态

- 状态：已接受
- 日期：2026-07-16

## 背景

后端引擎(feat-001~010)已交付并用真实 Ark 验证:问答 `/api/chat`、教学洞察 `/api/insights/*` 就绪;训练(E)、项目(F)**尚无 HTTP 端点**,`/api/chat` 也不接收 `task_type`/`learner_answer`。现有前端脚手架 `apps/web` 是 React19+Vite+原生 CSS 的三栏 mock UI(`api/client.ts` 直接 throw、`App.tsx` 喂 mockData),从未接真实后端。

本轮目标:把前端做成**可点、接真实后端**的双角色产品(学生端 + 讲师端),并达到 taste-skill(反 AI 套路前端框架)的质感标准,而非模板感 slop。

taste-skill 的适用性(诚实判定):它的自述 scope 是 landing/portfolio/redesign,并明确排除 dashboard/密集产品 UI/数据表格。我们的产品恰是**产品级双角色 UI**。因此**采纳它的通用反套路纪律**(排版/配色锁/圆角锁/图标库统一/完整交互态/对比度/动效克制/禁 em-dash),**不套用**它的营销页专属规则(hero 视口纪律/bento/scroll 劫持/marquee);技术选型上采纳它对"自拥有组件的现代产品 UI"点名的 shadcn/ui + Tailwind,dashboard 借 Radix。

## 决策

### 覆盖面与 scope 边界
- 本轮前端 = **学生端问答** + **讲师端洞察看板** 两个真实可用面。
- **训练(E)/ 项目(F)**:后端缺端点,归入**下一迭代**;本轮导航留入口 + 精心 empty state(标"下一迭代上线"),不放假数据假按钮。
- **真实鉴权登录、流式输出**:同样归入下一迭代。本轮身份用**顶部角色切换器(demo 模式,无登录)**,诚实标注无鉴权。

### 技术栈
- **React 19 + Vite + TypeScript**(沿用脚手架,不迁 Next——纯内部产品无 SSR/SEO 需求)。
- **Tailwind v4**(`@tailwindcss/vite` 插件)+ **shadcn/ui**(自拥有组件)+ **Radix** 原语 + **Motion**(`motion/react`)。
- 数据可视化用 **Recharts**,按 taste-skill 纪律覆写默认样式(去默认配色/网格,套锁定 accent + 中性底 + Geist)。
- 图标统一 **Phosphor**(禁手搓 SVG、禁混库)。
- **依赖钉版本**(现脚手架全 `latest`,不可复现,本轮改为固定版本)。

### 视觉语言(taste-skill 三档位)
- **Design Read**:学习型双角色产品 UI(对话工具 + 数据看板),面向学生与讲师,Linear/Notion 式冷静克制的产品美学。
- **档位**:`DESIGN_VARIANCE: 5` / `MOTION_INTENSITY: 3` / `VISUAL_DENSITY: 6`。
- 中性底(Zinc/Slate)+ **单一 accent 全站锁定**;字体 **Geist**(禁 Inter 默认、禁 serif 默认);**单一圆角尺度锁定**;深浅色双主题(整页锁一个主题,不中途翻转)。
- 动效只保留有意义的:消息进入、trace 节点展开、数字滚动、侧滑抽屉;禁 scroll 劫持/marquee/GSAP-for-show;`MOTION_INTENSITY>3` 的动效包 `prefers-reduced-motion` 回退。

### 页面结构
- **学生问答页**:三栏 = 左会话列表 / 中对话 / 右侧 **Tab 切「引用来源 / Agent Trace」**;回答里的引用角标 `[n]` 点击联动定位右侧来源卡。
- **讲师洞察看板**:**单页钻取式** = 顶部概览指标 → 知识点掌握度矩阵 → 薄弱排行 → 里程碑漏斗 → 侧滑个体档案(inline 讲师修正掌握度)。

### 状态与真实性
- 后端一次 `/api/chat` 真实 invoke 十几秒、同步无流式。等待期用**匹配最终布局的骨架屏**(禁通用 spinner)+ 分阶段节点提示(retrieve→answer→review),把延迟转化为"看得见引擎在工作"。
- 全套 loading / empty / error 态(会话空、洞察无数据、Ark 报错)。
- **不做假流式/假逐字打字**——后端不支持流,前端不假装。真实流式归下一迭代。

## 后果

- 正面:双角色产品可真实点通;信息架构完整(训练/项目占位就位,下次接端点改动小);质感有 taste-skill 纪律兜底,不出 slop;依赖钉版本可复现。
- 代价:引入 Tailwind/shadcn/Recharts/Motion 多个依赖与构建配置改动;需重做现有原生 CSS 三栏样式。
- 不可逆度:技术栈基座(Vite vs Next、Tailwind+shadcn)是较难回退的决策,故记此 ADR。视觉档位/页面结构可迭代调整,不属不可逆。

## 替代方案(未采纳)

- **纯原生 CSS 手写样式**:依赖最少,但难达 taste-skill 质感且易 CSS slop。
- **迁 Next.js**:当前纯内部产品无 SSR/SEO 需求,迁移成本无收益。
- **本轮就补训练/项目端点**:超出"只接已就绪后端"的 scope 决策,归下一迭代。
- **图表纯 CSS 手画**:曾考虑;用户选择引 Recharts 以备后续复杂趋势图。
- **真实/假登录**:后端无鉴权,假登录是"假装有系统",改用诚实的 demo 角色切换器。
