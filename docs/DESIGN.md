# DESIGN — AI 学习伙伴 技术实现方案

> 本文是**技术实现方案**(后端/引擎为主)。前端方案见 `docs/FRONTEND.md`(ADR-0007),愿景见 `docs/VISION.md`,术语见 `CONTEXT.md`,关键决策见 `docs/adr/`,原始需求见 `docs/PRD.md`。
> 状态:草案(2026-07-16)。冲突时以 VISION > 本文 > 脚手架现状为序。

## 0. 本文回答什么

如何把"学习引擎 + 课程包"双层架构、七大能力块,落到现有 monorepo 脚手架上,本轮真实交付"引擎骨架 + 一条纵切 + E/F/T 最小可运行版",其余标注扩展点。

## 1. 范围(口径 2,已锁)

| 类别 | 本轮代码落地 | 说明 |
|---|---|---|
| 引擎双层骨架 | ✅ 真实 | course_pack 可加载、Learner Model 持久化、真 StateGraph |
| A 课程问答 | ✅ 全量 | Agentic RAG,真 StateGraph,页码定位,拒答 |
| B Learner Model | ✅ 真实持久化 | 掌握度=系统推断+讲师修正 |
| C 个性化 | ✅ 纵切 | 深浅 + 薄弱前置补齐(画像注入) |
| D 主动建议 | ✅ 纵切 | 会话开场 + 收尾建议 |
| E 训练闭环 | ✅ 最小一轮 | 出题→批改→更新掌握度 |
| F 结课项目陪练 | ✅ 状态机可读写 | 里程碑状态机 + 达标判定(自述+片段) |
| T 教学洞察 | ✅ 只读接口 | per-course 聚合 |
| 扩展点(仅接口/字段) | ❌ 不实现 | 自适应路径、后台触达、真实产出物审查/代码判题、洞察闭环行动、VLM 图片解析、MCP 工具体系、运营评估 |

纵切主线:**A 问答 → 触发 B 掌握度更新 → C 个性化 → D 收尾建议**,端到端真实可跑可测。

## 2. 总体架构

```
┌──────────────────────────────────────────────────────────────┐
│  apps/web (React SPA)  三栏:对话 / 来源 / 轨迹 + 讲师洞察视图     │
└───────────────────────────────┬──────────────────────────────┘
                                │ HTTP / WS
┌───────────────────────────────┴──────────────────────────────┐
│  apps/api (FastAPI)                                            │
│  ┌──────────────┐  ┌──────────────────────────────────────┐  │
│  │  Learning Engine (领域无关)                                │  │
│  │  ┌────────────────────────────────────────────────────┐ │  │
│  │  │ 编排层 (LangGraph, ADR-0001/0004)                     │ │  │
│  │  │  顶层 Router 主图                                      │ │  │
│  │  │   ├─ 问答子图 (Retrieve/Rewrite/Answer/Review)        │ │  │
│  │  │   ├─ 训练闭环子图 (出题/批改/更新掌握度)                 │ │  │
│  │  │   └─ 项目陪练子图 (里程碑/达标判定)                      │ │  │
│  │  │  横切装饰: C 画像注入 · D 开场&收尾建议                  │ │  │
│  │  └────────────────────────────────────────────────────┘ │  │
│  │  Learner Model · 训练闭环 · 项目里程碑状态机 · 教学洞察读模型 │  │
│  └──────────────────────────────┬───────────────────────────┘  │
│  ┌──────────────────────────────┴───────────────────────────┐  │
│  │  Course Pack Loader (ADR-0002/0006)                       │  │
│  │  读 data/course_packs/<id>/{manifest,taxonomy,rubric,...}  │  │
│  └──────────────────────────────────────────────────────────┘  │
│  持久化: 业务库(SQLite+SQLModel, ADR-0005) · Chroma向量库         │
│         · LangGraph SqliteSaver(会话checkpoint)                 │
└───────────────────────────────┬──────────────────────────────┘
                                │
        ┌───────────────────────┴────────────────────┐
        │ 离线: Course Pack Ingestion (ADR-0006)        │
        │ HTML PPT/MD/PDF → AI提取 → chunks/候选taxonomy │
        └─────────────────────────────────────────────┘

  apps/mcp_servers/course_search: Course Search MCP (检索工具, V2 工具体系扩展点)
```

**引擎 / 课程包边界铁律**:引擎代码 import 不到任何 `ai_agent` 专属常量;所有课程特定内容经 `CoursePackLoader` 以数据注入。

## 3. 目录规划(在现有 monorepo 上演进)

```
apps/api/app/
  engine/                     # 【新】领域无关引擎
    orchestration/
      state.py                # TutorState (TypedDict, 跨图共享)
      main_graph.py           # 顶层 Router 主图
      subgraphs/
        qa_graph.py           # 问答子图 (承载 ADR-0001 图逻辑)
        training_graph.py     # 训练闭环子图 (E)
        capstone_graph.py     # 项目陪练子图 (F)
      decorators/
        personalization.py    # C 画像注入
        proactive.py          # D 开场 & 收尾建议
    learner_model/            # B: 掌握度读写、推断
    training/                 # E: 出题策略、Grader
    capstone/                 # F: 里程碑状态机、达标判定
    insights/                 # T: per-course 聚合只读模型
  course_pack/                # 【新】课程包契约
    loader.py                 # CoursePackLoader → CoursePack 对象
    schema.py                 # manifest/taxonomy/rubric 的 SQLModel/Pydantic schema
  ingestion/                  # 【演进现有】课程包摄取管线
    parsers.py                # HTML PPT / MD / PDF (现有基础上扩展)
    chunker.py                # (现有)
    extract.py                # 【新】AI 提取候选 taxonomy/题库
    service.py                # (现有) 建库编排
  persistence/                # 【新】业务库 (SQLModel, ADR-0005)
    models.py                 # learner/mastery/milestone_progress/exercise_attempt/question_bank/qa_history
  routes/                     # 【演进】chat(现有) + learner/training/capstone/insights(新)
  repositories/               # (现有,迁入 SQLModel)

data/
  course_packs/ai_agent/      # 【迁移】由 data/raw/ 迁入 (ADR-0002/0006)
    manifest.yaml
    taxonomy.yaml             # 候选,讲师可修正
    rubric.yaml
    questions/                # 题库(预置+LLM候选)
    materials/                # HTML PPT / MD / PDF 原始资料
  business.sqlite             # 业务库 (gitignore)
  checkpoints.sqlite          # LangGraph 会话 checkpoint (gitignore)
  chroma/                     # 向量库 (gitignore)
```

## 4. 编排层设计(ADR-0001 + 0004)

### 4.1 TutorState(跨图共享)

顶层与子图共享同一 TypedDict。核心字段:

- 请求上下文:`learner_id`、`course_pack_id`、`query`、`task_type`
- 检索:`retrieved_chunks`、`citations`、`retry_count`、`max_retry`、`evidence_sufficient`
- 生成/评审:`answer`、`review_verdict`、`refused`
- 画像(C):`mastery_profile`、`weak_topics`
- 建议(D):`session_opener`、`closing_suggestion`
- 训练(E):`current_question`、`grade_result`
- 项目(F):`current_milestone`、`milestone_verdict`
- 轨迹:`trace`(节点序列 + 每节点 IO)

### 4.2 顶层主图

Router 节点判 `task_type` → `add_conditional_edges` 分派:
`rag_answer/direct_answer → 问答子图`;`grade_homework → 训练子图`;`capstone → 项目子图`。
进入前挂 D 开场装饰,退出前挂 D 收尾装饰。

### 4.3 问答子图(承载 GRAPH-001/002/003 硬验收)

`retrieve → evidence_check`:
- 证据足 → `answer → review`
- 不足且 `retry_count < max_retry` → `query_rewrite → retrieve`(真实回环)
- 不足且超限 → `refuse`(拒答,不编造页码)

`review` 条件边:通过 → `final`;可修 → `answer`;不可修 → `refuse`。终点 `END`。
C 画像注入:`retrieve` 前按 `weak_topics` 扩展检索范围;`answer` prompt 注入 `mastery_profile` 调深浅。

### 4.4 训练闭环子图(E,最小一轮)

`select_question(出题策略:预置题库匹配薄弱点,不足则 LLM 依 RAG 证据生成) → (学员作答) → grade(Grader 按 Rubric 批改) → update_mastery(写回 mastery 表)`。

### 4.5 项目陪练子图(F)

`load_milestone(读 milestone_progress) → gate(达标判定:基于自述+贴片段) → advise(针对性建议/推进)`。产出物真实审查为 V2,`artifact_summary` 字段占位。

## 5. 持久化(ADR-0005)

- **业务库** `business.sqlite`(SQLModel):表见 ADR-0005 §决策(learner / mastery / milestone_progress / exercise_attempt / question_bank / qa_history)。`topic_id`、`course_pack_id` 建索引。
- **会话库** `checkpoints.sqlite`:LangGraph `SqliteSaver`,物理分离。
- **向量库** `data/chroma/`:Chroma,维度以 Ark 多模态接口实测为准(ADR-0003)。
- 教学洞察(T)= 直接对业务库做 `GROUP BY topic_id / milestone` 的只读聚合,不进 StateGraph。

## 6. 课程包与摄取(ADR-0002 + 0006)

- `CoursePackLoader.load(course_pack_id)` 读约定目录 → `CoursePack` 对象(manifest/taxonomy/rubric/题库/向量句柄)。引擎只依赖此对象。
- 摄取管线(离线):HTML PPT 去壳按页取正文(保 slide_no)、MD 直取、PDF 抽文本 → 分块(带元数据)→ Ark 多模态 embedding 入 Chroma;AI 提取**候选** taxonomy/题库,讲师审核沉淀。
- MVP 仅文本层;图片/图表 VLM 解析为 V2(embedding 模型多模态已铺路)。

## 7. 模型接入(ADR-0003)

- LLM(VLM):Ark `/chat/completions`,endpoint `ep-20260714205835-n286q`,标准 OpenAI 兼容,可直接用 `langchain_openai`。
- Embedding:Ark `/embeddings/multimodal`,endpoint `ep-20260714205846-9ktww`,input 包 `[{"type":"text","text":...}]`,需自定义客户端。
- 配置经 `.env`(gitignore),`EMBEDDING_PROVIDER=ark_multimodal`。密钥永不进 git/文档。

## 8. API 面(在现有 routes 上演进)

| 路由 | 能力 | 本轮 |
|---|---|---|
| `POST /chat`(现有,重写接 StateGraph) | A/C/D 纵切 | ✅ |
| `GET /learner/{id}` | B 读档案 | ✅ |
| `PATCH /learner/{id}/mastery` | B 讲师修正 | ✅ |
| `POST /training/question` `POST /training/grade` | E | ✅ 最小 |
| `GET/PATCH /capstone/{learner_id}` | F 里程碑 | ✅ 读写 |
| `GET /insights/courses/{course_pack_id}` | T per-course 聚合 | ✅ 只读 |
| `/admin` `/version` `/health`(现有) | 运维 | 保留 |

## 9. 与脚手架的差距与迁移

| 现状 | 动作 | 依据 |
|---|---|---|
| `agent/graph.py` 手写顺序链 | 重写为分层 StateGraph | ADR-0001/0004 |
| 无 course_pack 概念,`data/course_materials/` | 引入 CoursePackLoader,迁 `data/raw/`→`data/course_packs/ai_agent/` | ADR-0002/0006 |
| 原生 sqlite migrations | 迁 SQLModel + 领域表 | ADR-0005 |
| ingestion 仅解析建库 | 增 AI 提取候选 taxonomy/题库 | ADR-0006 |
| embedding 未定 | Ark 多模态客户端 | ADR-0003 |
| 无 Learner Model/训练/项目/洞察 | 新建 engine 子模块 | 七块 |
| Course Search MCP mock | 保留为 V2 工具体系扩展点 | — |

## 10. 验证策略

- 单测分层:主图路由、各子图独立、持久化 repo、CoursePackLoader、摄取解析。
- 纵切集成测试:A→B→C→D 端到端(含拒答路径、重试退出 max_retry)。
- GRAPH-001/002/003 按 PRD 硬验收(存在 State/Node/Edge/Conditional Edge/END + 真实 Rewrite 重试 + max_retry 退出)。
- 评估:沿用 `evals/` 目录,补拒答/引用正确性用例。
- `init.sh` 收敛为 Python 栈的可运行校验(见下一步)。
