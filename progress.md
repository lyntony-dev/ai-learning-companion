# Session Progress Log

## Current State

**Last Updated:** 2026-07-26
**Active Feature:** 三梯队生产化改造**全部完成**。**Tier 1**(feat-016/FE-011/017/018)、**Tier 2**(feat-019/020/021)、**Tier 3-7**:代码分割 + 前端单测(vitest)+ CI + 北极星指标(feat-022)+ 诚实节点级流式 SSE(feat-023)。MVP 已端到端验证,pytest 154 passed/1 skipped、eval 4/4、前端 typecheck/lint/test(8)/build 四关零告警且构建已分包。

## Status

### What's Done

- [x] 设计阶段:VISION / CONTEXT / DESIGN + ADR 0001–0007 / feature_list / init.sh
- [x] **后端 feat-001~010**(领域无关 LangGraph 学习引擎 + 课程包纵切,详见下方分条与 feature_list.json)
- [x] **前端 FE-001~005**(React 双角色 SPA):
  - FE-001 基座 + 双角色外壳(钉版本、AppShell、RoleSwitcher、主题锁、reduced-motion)
  - FE-002 数据层(真实 fetch,types 逐字段对齐后端,Vite proxy)
  - FE-003 学生问答页(三栏、角标[n]联动、四态、接 /api/chat)
  - FE-004 讲师洞察看板(概览/矩阵/排行/漏斗 Recharts + 侧滑 inline 修正)
  - FE-005 占位页 + MVP UX 修复:角色导航守卫、课程浏览/详情页 + 只读 courses 后端、引用来源可点直达资料、会话列表持久化 + 刷新恢复
- [x] **feat-011 历史对话全保真持久化(后端)**:messages 表加全文 content + trace_id(迁移 002);/api/chat 落全文并关联 assistant trace_id;list_messages 回吐;pytest 68 passed / eval 4/4;TestClient 端到端冒烟(长问题全文 round-trip + trace_id 回取 9 events)
- [x] **FE-006 应用内预览抽屉 + 历史 Agent Trace 懒加载(前端)**:资料/引用改 Radix Dialog 抽屉预览(html/pdf iframe、md react-markdown、py/txt 代码);后端材料端点改 inline 处置;历史恢复全文回答 + 按 trace_id 懒加载 Agent Trace;typecheck/lint/build 三关通过零告警
- [x] **feat-012 训练闭环(E)+ 项目(F)HTTP 端点**:直接调引擎(与 insights 一致,不走图/trace)暴露 4 端点——POST /api/training/courses/{id}/questions|grade、GET/POST /api/capstone/courses/{id}/milestones[/{mid}/assess];出题/批改响应永不含 reference_answer(服务端 get_question 按 id 重载判分);项目返回全量里程碑列表。新增 SqlTrainingService.get_question + SqlCapstoneService.list_milestones(只读 CoursePack+业务库,引擎零硬编码)。pytest 95 passed / eval 4/4;真实起后端 4 端点冒烟全通(短自述 in_progress、充分自述 passed、未知题 404)
- [x] **FE-007 学生端训练闭环页 + 项目陪练页(前端)**:training/capstone 占位替换为真实交互页;训练页出题→作答(Enter 换行不发送,点击提交)→批改结果(逐维进度条+反馈+掌握度徽章);项目页进度总览+全量里程碑行(状态图标/当前高亮/可选)+选中里程碑提交自述判定;api/{training,capstone}.ts + types + useTraining/useCapstone hooks;/training、/capstone 套 RequireRole=student;typecheck/lint/build 三关零告警;真实前后端端到端冒烟通
- [x] **feat-013 项目陪练引导数据(课程包 + API 透传)**〔superseded by feat-014〕:manifest.yaml capstone 段扩展项目级 overview/background/final_deliverable + 每里程碑 deliverable/hint/sample_report(全部可选,默认空串向后兼容);经 schema→loader→service.list_milestones→API 透传
- [x] **FE-008 项目陪练引导 UI(前端)**〔superseded by FE-009〕:capstone.tsx 项目说明书卡 + 交付要求/提示 + 可折叠范例提交面板 + 填入试试按钮
- [x] **feat-014 项目陪练重设计:立项向导 + 个性化清单(后端)**:诊断——"写自述→LLM 判定"是空壳,学生不知该写什么、什么算"满足需要"。重设计为:学生立项(goal/audience/difficulty)→引擎基于课程包里程碑 + RAG 证据用 LLM 收敛"项目卡"(title/scope/tech_stack)并为每个里程碑生成"绑定到学生自己项目的可勾选清单"→勾选推进,里程碑状态由勾选完成度派生写回 milestone_progress。新增 CapstoneProject 表;删自述判定/current_milestone/list_milestones + 删 capstone LangGraph 子图(/chat 本就不走,无回归);manifest 清除令人迷惑的 sample_report。LLM 不可用时按 deliverable 句读拆解保底清单(离线可跑)。pytest 92 passed / eval 4/4;真实起后端冒烟:向导态无清单→立项生成卡+清单(Ark 401 时走保底)→勾满里程碑 passed、current 前移、未知 item 404
- [x] **FE-009 项目陪练重设计:立项向导 + 项目卡 + 个性化清单(前端)**:capstone.tsx 全重写——未立项:项目说明书 + 立项向导多字段表单(想做什么 Agent 必填/面向谁/预期难点选填,点击按钮提交非回车);已立项:进度总览 + 项目卡(标题/范围/技术选型徽章)+ 每里程碑可勾选清单(乐观更新推进状态)。api/client.ts 加 apiPatch;types/capstone.ts/useCapstone 重写;typecheck/lint/build 三关零告警
- [x] **feat-015 学生登录与学习者身份(后端,ADR-0008)**:取代硬编码 demo_user 无状态。轻量账号(用户名+密码,bcrypt 哈希 + stdlib HMAC 自签 token,不引 JWT 库);新增 LearnerAuth/LearnerProfile 两表(create_all 自动建,非破坏);画像三组(基础资料/学习目标偏好/自动画像聚合 Mastery);auth 模块(security/service/deps)+ routes/auth.py(/api/auth register|login|me);chat/training/capstone 路由统一 resolve_learner_id——Authorization token 身份覆盖请求体,无 token 回退访客 demo_user 保持"打开即用"。pytest 103 passed / eval 4/4;真实起后端 curl 端到端冒烟:register/login/me/patch/401/422 全符合预期
- [x] **FE-010 学生登录与画像 UI(前端,ADR-0008)**:AuthProvider+useAuth(localStorage 持久化刷新恢复)+ getStoredToken 供 client 注入 Authorization;api/auth.ts + ui/input.tsx;routes/login.tsx(登录/注册切换,点击提交非回车,成功跳 /student,可访客体验)+ routes/profile.tsx(需登录否则跳 /login;基础资料/学习目标偏好可编辑 + 自动画像只读徽章;PATCH /me;退出登录);App.tsx 加 /login、/profile;AppShell 学生态登录按钮/用户菜单+我的画像入口;useCapstone/useTraining 用 useAuth().learnerId 取代 demo_user 硬编码;typecheck/lint/build 三关零告警
- [x] harness 更新:AGENTS.md(环境初始化/本地运行/校验/前端质感纪律/解耦铁律)、feature_list.json 补 FE-001~006 与 feat-011、init.sh 补前端段、session-handoff.md
- [x] **feat-016 讲师鉴权 + 角色权限(后端,ADR-0009)**:复用 ADR-0008 轻量基建,角色随 token 承载(payload 加 `role`,无需 DB 迁移);讲师 `learner_id=tea_<username>`,注册须带邀请码(`AUTH_TEACHER_INVITE_CODE`,dev 占位 `dev-teacher-invite`);`auth/security.sign_token(...role="student")`、`auth/service`(role_of/STUDENT_PREFIX/TEACHER_PREFIX,register 加 role/invite_code,login/get_account 回 role)、`auth/deps`(current_identity/require_teacher:无 token 401、非讲师 403)。**教学洞察三端点全部 require_teacher 守卫**;`mastery-corrections` 的 `updated_by` 改由已鉴权讲师身份派生(防伪造,请求体 updated_by 忽略)。schema 加 role/invite_code。pytest 119 passed / 1 skipped、eval 4/4;新增 5 讲师用例 + test_http_requires_teacher(401/403)。⚠️ 生产必须覆盖 AUTH_TEACHER_INVITE_CODE 与 AUTH_TOKEN_SECRET
- [x] **FE-011 讲师登录 + 角色守卫(前端,ADR-0009)**:**删除无鉴权 demo RoleSwitcher 安全漏洞**;role 改由 `useAuth().role` 派生(role.tsx 变透传壳,useRole 读 auth);login.tsx 加学生/讲师注册切换 + 邀请码输入,按 res.role 跳转;App.tsx RequireRole 讲师页未登录→/login;AppShell 移除切换器,鉴权驱动头部 + 讲师 Chalkboard 徽标;LearnerDrawer 移除 INSTRUCTOR 常量,乐观显示用 session.username,correctMastery 不再回传 updated_by。types 加 role/invite_code。typecheck/lint/build 三关零告警
- [x] **feat-017 容器化部署与 CORS 策略(ADR-0010)**:一键 `docker compose up --build` 起完整应用(http://localhost:8080)。`deploy/api.Dockerfile`(uv 装依赖,WORKDIR 保持 parents[5] 层级正确定位 course_packs,uvicorn)、`deploy/web.Dockerfile`(pnpm build → nginx 静态)、`deploy/nginx.conf`(SPA fallback + /api 同源反代 api:8000,免 CORS)、`deploy/.env.deploy.example`(生产密钥占位)、根 `docker-compose.yml`(api healthcheck + web depends_on service_healthy + 命名卷 tutor-data 持久化)、`.dockerignore`。`config.cors_allow_origins` + `cors_origins_list`;`main.py` 仅当 `CORS_ALLOW_ORIGINS` 非空才挂 CORSMiddleware(默认零行为变化,供前后端分离)。pytest 122 passed / 1 skipped(+3 test_cors.py)、eval 4/4、前端三关零告警。本机无 compose 插件,部署产物静态审阅(YAML/路径校验通过)
- [x] **feat-018 生产配置固化 + 结构化日志 + README(发布下限收尾)**:config 抽 DEV_TOKEN_SECRET/DEV_TEACHER_INVITE 常量 + ConfigError + is_production + `validate_production()`——`APP_ENV=production` 时 dev 占位密钥仍在则**启动即失败**(fail-fast);main.py create_app 调用校验并按 is_production 切 JSON 日志。logging.py 重写为 handler-based + `JsonLogFormatter`(生产单行 JSON 便于采集,本地文本),中间件改 extra 传字段。补齐**仓库根 README.md**(愿景/引擎+课程包架构/技术栈/本地开发/验证/部署/文档地图);init.sh 补容器化部署段。pytest 124 passed / 1 skipped(+2 生产校验)、eval 4/4、JSON 日志 smoke 验证。**Tier 1 发布下限全部完成**
- [x] **feat-019 画像驱动个性化(Tier 2-4)**:把已采集但未使用的 `LearnerProfile`(background/learning_goal/preferred_difficulty)接入 C 个性化装饰与训练出题。`SqlLearnerModel.learner_profile(learner_id)` 按 PK 读画像(EmptyLearnerModel 返回 {});personalization.opener 经 getattr 守卫注入 `state['learner_profile']`(trace 标 profile=y/n);TutorState 加 `learner_profile: dict`;qa_graph `_build_answer_prompt` 追加 `_learner_profile_hint`(背景/目标类比 + `_DIFFICULTY_STYLE` 讲解风格,截断 120 字,不改引用纪律);training `_target_difficulty` 改为掌握度目标难度与 preferred_difficulty 取序数平均(偏好拉半档),未设/非法偏好回退纯掌握度。**空画像=访客/未登录/新学员行为零回归**(画像是学员属性非课程内容,不违反引擎领域无关铁律)。前端 profile.tsx 已采集三字段无需改动。新增 tests/test_personalization_profile.py 9 条(hint 空/齐全/非法难度;learner_profile 读/缺失/Empty;_target_difficulty 无画像/上拉/下拉/空偏好)。pytest 133 passed / 1 skipped(+9)、eval 4/4 未回归
- [x] **feat-020 讲师审核沉淀流(Tier 2-5,ADR-0006 飞轮)**:LLM 候选题(source=LLM_GENERATED、approved_by 空)此前只写不审,飞轮不闭环。`SqlTrainingService` 加 `list_candidate_questions`(只列未审 LLM 候选,含参考答案+知识点名)/`approve_question`(写 approved_by 沉淀为优先出题来源,幂等)/`reject_question`(删待审候选,已沉淀不可删)。routes/training.py 加 3 端点(GET candidates、POST approve、POST reject)全 `require_teacher` 守卫,approved_by 以认证讲师派生。前端:useCandidates hook(四态+审核后本地摘除)+ CandidateReview 组件 + teacher.tsx Tabs(教学洞察/候选题审核)。**候选参考答案仅讲师可见,学生端出题/批改仍不含**。新增 tests/test_question_review.py 8 条。pytest 141 passed / 1 skipped(+8)、eval 4/4、前端三关零告警
- [x] **feat-021 我的学习档案聚合页(Tier 2-6)**:学生此前无处一览自己的学习轨迹。`SqlLearnerModel.learning_archive(learner_id, course_pack_id)` 聚合掌握度分布(known/fuzzy/unknown + 仅 taxonomy 内知识点列表,含 system_inferred/instructor_corrected 来源)、练习记录(累计作答/平均分/最近 5 次)、结课项目进度(目标/里程碑通过数/各里程碑状态)。schemas/archive.py 7 模型;routes/archive.py `GET /api/archive/courses/{id}`,本地 `require_learner_id`(无 token→401),**learner_id 仅取 token 身份不接受请求参数指定他人(不越权只读自己)**,课程包缺失→404;main.py 注册。前端:api/types.ts 加 7 档案类型(snake_case 对齐)、api/archive.ts、hooks/useArchive.ts(四态+reload)、routes/archive.tsx(未登录 Navigate /login;loading skeleton/error 重试/无记录 EmptyState/success 三卡;token 化配色圆角 + Phosphor 图标 + 无 em-dash);App.tsx 加 /archive(RequireRole student);AppShell 加“学习档案”导航(仅 student)。**画像/档案是学员属性非课程内容,知识点/里程碑口径来自注入 CoursePack,不违反引擎领域无关铁律;访客/未登录零回归**。新增 tests/test_archive.py 6 条(聚合口径/本人隔离/项目进度/HTTP 401+200+404)。pytest 147 passed / 1 skipped(+6)、eval 4/4、前端三关零告警。**Tier 2 产品价值全部完成**
- [x] **feat-022 北极星指标看板 + 代码分割 + 前端单测 + CI(Tier 3-7)**:讲师端加按课程包聚合的五组北极星指标——engagement(活跃学习者/问答轮次/练习次数)、honesty(问答轮次/拒答数/**拒答率**——诚实铁律可观测)、mastery_progress(追踪知识点/known 数/率)、practice_quality(练习次数/平均分 0~1)、capstone_funnel(立项/结课/率,结课=全部里程碑通过)。engine/insights/service.py 加 `north_star_metrics(course_pack_id)`;schemas/insights.py +6 模型+NorthStarMetricsResponse;routes/insights.py `GET /api/courses/{id}/metrics`(require_teacher,身份取 token 防伪造)。前端:types +6 类型、insights.ts getNorthStarMetrics、useMetrics hook、MetricsPanel 组件、teacher.tsx 加“北极星指标”Tab。工程化:vite.config.ts `manualChunks`(vendor-charts/markdown/motion,消除 >500kB 告警)+ App.tsx 路由全 `React.lazy`+Suspense;vitest 落地(vitest.config.ts + src/lib/slug.test.ts 8 条镜像后端)+ package.json `test`=vitest run;`.github/workflows/ci.yml`(后端 uv+pytest+eval,前端 pnpm typecheck/lint/test/build,--frozen-lockfile)。tests/test_metrics.py 6 条全过
- [x] **feat-023 诚实节点级流式输出 SSE(Tier 3-7 收尾)**:此前问答同步等十几秒,前端只能计时臆测进度。新增 `POST /api/chat/stream`(SSE text/event-stream)经 `graph.stream(stream_mode="values")` 逐节点吐**真实** progress 事件(personalize_opener→router→qa→retrieve→answer→learner_update→closing_advice),整图 **review 校验后**再吐 final 事件携带已校验 answer/citations/trace_id。**诚实铁律:绝不流式吐未经 review 的原始 token**(review 可能拒答/降级),故做节点级进度流而非 token 流。routes/chat.py 抽出 `_extract_result/_persist_turn/_sse` 与同步 /chat 共用,**同步 /chat 保持不变、访客路径零回归**。前端 api/chat.ts `streamChat`(SSE 解析+token 注入)、useChat.send 流式优先+失败**优雅回退** postChat、types/view.ts +progressNode、PendingAnswer 接 activeNode 按真实节点点亮阶段(无流式回落计时示意)、ChatMessage 透传。tests/test_chat_api.py 加 test_chat_stream_emits_progress_then_validated_final。pytest 154 passed / 1 skipped(+1)、eval 4/4、前端四关零告警。**三梯队全部完成**

### What's Next

- **三梯队(Tier 1/2/3)全部完成。** 作为完整应用版本,后续 V2 候选(非本轮范围):真实 Ark 长跑压测与流式端到端浏览器验证、班级维度洞察、图片多模态索引、题库沉淀飞轮的批量导入、E2E(Playwright)与前端组件测试扩面、指标持久化埋点与时间序列趋势。⚠️ 真实 Ark API key 若过期需更新 `.env` 的 LLM_API_KEY/EMBEDDING_API_KEY 才能验证真实 LLM 生成质量与 SSE 长跑。生产部署必须覆盖 `AUTH_TOKEN_SECRET` 与 `AUTH_TEACHER_INVITE_CODE`。

### 后端 feat-001~010(历史)

- [x] 设计阶段:VISION / CONTEXT / DESIGN + ADR 0001–0006 / feature_list / init.sh
- [x] feat-001 建 py3.11 venv + install;修 pyproject 打包;Settings 补 Ark 字段;pytest 15 passed
- [x] feat-002 SQLModel 六表 + 4 枚举(app/persistence/);独立 BUSINESS_DB_URL;pytest 19 passed
- [x] feat-003 迁移 materials + manifest/taxonomy/rubric + CoursePackLoader;pytest 26 passed
- [x] feat-004 摄取管线(解析/分块/embeddings/vector_store/pack_service)+ AI 提取(llm/extract);pytest 34 passed;真实 Ark embedding(dim=2048)+ 端到端 ingest + LLM 候选提取冒烟通过
- [x] feat-005 编排层重写为真 LangGraph StateGraph(app/engine/:state/qa_graph/main_graph/decorators/retrieval),重写 /chat,删手写链;pytest 41 passed;真实 Ark 检索+Doubao 生成 E2E 冒烟通过
- [x] feat-006 纵切 A→B→C→D:Learner Model(SqlLearnerModel)读写掌握度,learner_update 节点写回,C 检索按 weak_topics 扩展,D opener/closing 真实数据;pytest 44 passed;真实两轮 E2E 通过
- [x] feat-007 训练闭环子图(E):TrainingService(出题/批改/更新掌握度)+ 真训练子图(select_question→grade→update_mastery / 未作答 await_answer),主图 grade_homework 接真子图;训练批改可达 known;pytest 51 passed;真实 Ark 出题+批改 E2E 通过
- [x] feat-008 项目里程碑状态机(F):CapstoneService(定位/判定/建议)+ 真项目子图(locate_milestone→assess→advise / 全达标 congratulate),主图 capstone 接真子图;milestone_progress 状态机不回退;pytest 58 passed;真实 Ark 达标判定 E2E 通过
- [x] feat-009 教学洞察(T):SqlInsightsService(GROUP BY topic_id/milestone 只读聚合 + weak_ranking + 讲师修正掌握度)+ routes/insights.py(GET /insights/courses/{id}、learners/{id}、POST mastery-corrections);pytest 67 passed
- [x] feat-010 验证覆盖与文档收尾:分层单测全绿 + 纵切集成;新增 evals 质量门禁(qa_quality.json 4 例:2 引用正确性 + 2 拒答;qa_quality_runner.py 离线判分器复用 qa_graph 阈值口径;test_evals_qa_quality.py pytest 门禁);校对 init.sh 验证段;pytest 68 passed,1 skipped;独立 eval runner 4/4 通过

#### 后端 V2 方向(历史记录)

- 后续 V2 方向见各 ADR/DESIGN 占位:图片多模态索引、题库/taxonomy 讲师审核沉淀流、capstone 真实产出物接入、班级维度洞察、/chat 暴露 E/F 交互。

## Decisions Made

- **feat-009 只读聚合 + 讲师修正**:SqlInsightsService 只针对单课程包(不做班级维度,CONTEXT 口径)。course_insights 按 topic_id×level/topic_id(做题均分)/milestone×status 三组 GROUP BY 聚合,只保留 taxonomy 内知识点;weak_ranking 按 unknown+fuzzy 降序。correct_mastery upsert 标 INSTRUCTOR_CORRECTED+updated_by(最高优先级,系统推断不覆盖),拒 taxonomy 外 topic/空 updated_by。路由 GET /api/insights/courses/{id}(+ learners/{id})只读、POST mastery-corrections;课程包不存在→404,非法修正→422。

- **feat-008 里程碑状态机不回退**:current_milestone 按 CoursePack 里程碑序列定位首个未 passed;assess 证据不足(自述<20 字)先拦(不消耗 LLM),否则 LLM 判定 passed/reason/advice(启发式回退按自述长度);写 milestone_progress passed→PASSED / 否则 IN_PROGRESS,已 PASSED 不回退;artifact_summary 存自述片段作 V2 产出物接入占位。子图 locate_milestone→条件边→assess→advise / 全达标 congratulate;学员自述取 State.query。

- **feat-007 训练闭环可达 known**:出题按 weak_topics 选知识点,题库(讲师 approved 优先)不足则 LLM 依 RAG 证据生成候选题(source=llm_generated,approved_by 空待审核 ADR-0006),生成用「课程名+知识点」锚定检索+约束只依据材料防跑题;Grader 按 rubric(by_course_focus→default_dimensions)逐维打分加权(启发式 token 重合度回退),score>=0.8 达 known、>=0.4 fuzzy,与问答仅到 fuzzy 区分;讲师 instructor_corrected 仍不被批改覆盖。
- **交互式训练两段式**:select_question 后条件边 route_after_select——带 learner_answer→grade→update_mastery,未带→await_answer(先出题回给学员,下次请求带作答再批改),避免把出题与批改强耦合为一次同步调用。TutorState 加 learner_answer;build_main_graph 加 training_service 参数(注入才替换 _stub)。

- **feat-006 掌握度语义**:问答只算"接触",最高标 fuzzy;known 只由训练闭环(E)按 Rubric 产生。系统推断不覆盖讲师修正(instructor_corrected 优先级最高)。拒答轮不推断掌握度,但仍记 qa_history(refused=True)。
- **Learner Model 一体两面**:同一个注入对象既供 C/D 读(profile/weak_topics)又供 B 写(record_qa_turn);main_graph 参数从 mastery_provider 收敛为 learner_model。知识点匹配用注入的 CoursePack.taxonomy(token 命中,限被检索命中的 course_id),引擎零课程硬编码。
- **C 检索扩展**:qa_graph.retrieve 按 weak_topics 并入检索术语并放大 top_k(trace 标 weak_expanded),实现"薄弱前置知识点扩展检索范围"。

- **feat-005 真 StateGraph 分层**:顶层 Router 主图(personalize_opener→router→{qa/training/capstone}→closing_advice→END)+ 问答子图(retrieve/evidence_check/query_rewrite/answer/review/final/refuse,两处 add_conditional_edges,query_rewrite→retrieve 真实回环)。满足 GRAPH-001/002/003 硬验收。手写顺序链 agent/graph.py 作为 ADR-0001 反面教材已删除。
- **trace override + 显式累积**:子图与主图共享 trace 通道,若用 append reducer,子图返回的完整列表会被父图再追加导致重复;改用 `_keep_last` override + 每节点 `append_trace(state, ev)` 显式累积,子图边界不重复。
- **检索/生成可注入**:Retriever 协议 + VectorStoreRetriever;/chat 用 Depends(get_retriever) 便于测试注入 FakeRetriever;LLM 走 get_llm_client。训练/项目子图本轮为合法 stub(feat-007/008 填充)。
- **agent/models.py 裁剪**:编排层迁 app.engine 后,仅保留 API 响应层复用的 Citation/AgentTraceEvent DTO。

- **feat-004 embedding 走多模态接口**:Ark embedding 模型是 doubao-embedding-vision,必须 POST `/embeddings/multimodal`(input=`[{type:text,text:...}]`),标准 `/embeddings` 不可用;实测 dim=2048。图片索引 V2 可复用同一客户端。
- **索引/检索向量都由外部 client 产出**:VectorStore 只存/查向量,不内建 embedding,使 provider(mock/ark)可切换且维度一致;按 `pack_<id>` 分 collection,cosine 空间。
- **AI 提取产物一律 candidate**:extract.py 用 LLM 抽候选 topics/questions,严格 JSON 解析失败回退 section 启发式;沉淀 approved 须讲师审核(ADR-0006)。
- **新旧摄取隔离**:新增 `pack_*`/`embeddings`/`vector_store`/`extract` 与课程包契约耦合;旧 `ingestion/{parsers,chunker,service}.py`(绑 course.json + RAG sqlite)保持不动。

- **feat-003 课程包 = 约定目录 + 纯数据**:manifest.yaml(课程+里程碑) / taxonomy.yaml / rubric.yaml;引擎只依赖 CoursePack 对象,零硬编码(ADR-0006)。
- **materials 入 git,node_modules 排除**:迁移时 rsync `--exclude node_modules`;course_packs(1.6M)是课程资产入库,data/chroma 与 *.sqlite 仍 gitignore。
- **Loader 校验前置**:load 时校验 manifest id 与目录名一致、声明的资料真实存在,避免磁盘漂移(fail fast)。
- **feat-002 业务库物理分离**:SQLModel + `BUSINESS_DB_URL`(data/business.sqlite),不改脚手架原生 sqlite3 库(data/app.sqlite)。
- **`.env` 相对路径 / 路由前缀**:测试须在 apps/api 下跑;health=`/healthz`,version=`/api/version`。

## Files Modified This Session

- `scaffold/apps/api/pyproject.toml` — build-system + packages + sqlmodel + pyyaml
- `scaffold/apps/api/app/core/config.py` — Ark 字段 + business_db_url
- `scaffold/apps/api/app/persistence/*` — 六领域表 + engine/session (feat-002)
- `scaffold/apps/api/app/course_pack/*` — CoursePack schema + Loader (feat-003)
- `scaffold/apps/api/app/ingestion/{pack_parsers,pack_chunker,embeddings,vector_store,pack_service,extract}.py` — 摄取管线 (feat-004)
- `scaffold/apps/api/app/llm/{client,__init__}.py` — LLM 客户端(Ark /chat/completions + mock) (feat-004)
- `scaffold/apps/api/app/engine/**` — 领域无关引擎:orchestration(state/main_graph/subgraphs{qa,training,capstone}/decorators)+ retrieval + learner_model + training + capstone + insights (feat-005~009)
- `scaffold/apps/api/app/routes/{chat,insights}.py` — chat 接 build_main_graph;insights 教学洞察(T)三端点;main.py 注册 insights_router
- `scaffold/apps/api/app/schemas/insights.py` — 教学洞察 API schema (feat-009)
- `data/course_packs/ai_agent/{manifest,taxonomy,rubric}.yaml` + `materials/` — 迁移+约定文件
- `scaffold/apps/api/tests/test_{config_env,persistence_models,course_pack_loader,ingestion_pipeline,engine_graph,vertical_slice,training_graph,capstone_graph,insights}.py` + 重写 test_chat_api.py — 测试
- `init.sh` / `feature_list.json` — 校验命令与证据
- **前端 scaffold/apps/web**(FE-001~005):`src/{main,App}.tsx`、`src/lib/{theme,role}.tsx`、`src/components/layout/{AppShell,RoleSwitcher,RightPanel}.tsx`、`src/routes/{student,teacher,training,capstone,courses,course-detail}.tsx`、`src/components/chat/*`、`src/components/sources/{SourceCard,SourcesPanel}.tsx`、`src/components/trace/*`、`src/components/insights/*`、`src/hooks/useChat.ts`、`src/api/{client,chat,insights,courses,types}.ts`、`src/styles/globals.css`;后端配套 `app/routes/courses.py` + `app/schemas/courses.py` + `main.py` 注册。
- **harness(本次)**:`AGENTS.md` 重写、`feature_list.json` 补 FE-001~005、`init.sh` 补前端段、`session-handoff.md`。

## Evidence of Completion

- [x] Tests pass: `cd scaffold/apps/api && .venv/bin/pytest -q` → `103 passed, 1 skipped, 1 warning`(feat-015 学生登录:+11 tests/test_auth_api.py;feat-014 重设计前为 92 passed)
- [x] CoursePackLoader 端到端加载 ai_agent:4 门课 + 6 里程碑 + 14 知识点 + rubric
- [x] materials 迁移:115 文件,无 node_modules
- [x] 真实 Ark 冒烟(export repo 根 .env):`/embeddings/multimodal` dim=2048;端到端 parse→chunk→embed→Chroma→query 命中;真实 LLM 提取 4 候选知识点+2 候选题
- [x] feat-005 真 StateGraph:GRAPH-001/002/003 测试通过;真实 E2E(Ark 检索+Doubao 生成)trace 无重复、带引用、C/D 装饰生效
- [x] feat-010 evals 质量门禁:`.venv/bin/python ../../evals/runner/qa_quality_runner.py` → `4/4 cases passed`(2 引用正确性 + 2 拒答);pytest `test_evals_qa_quality.py` 门禁纳入全量套件

## Notes for Next Session

- venv 在 `scaffold/apps/api/.venv`(py3.11.15);跑测试须在 `scaffold/apps/api` 目录下。
- 依赖:fastapi/sqlmodel/sqlalchemy/pyyaml/beautifulsoup4/pypdf/chromadb(1.5.9)/httpx/langgraph(1.2.9)/langgraph-checkpoint-sqlite。
- 业务库=`data/business.sqlite`(gitignore);脚手架库=`data/app.sqlite`;course_packs 入 git。
- 真实 Ark 冒烟须先 export repo 根 `.env`(pytest 进程不自动载),否则 `test_ark_multimodal_embedding_smoke` 跳过。
- 课程包约定:`data/course_packs/<id>/{manifest,taxonomy,rubric}.yaml` + `materials/` + `questions/`(待 feat-007)。
- taxonomy/题库均为 candidate,待讲师审核沉淀(approved 字段已埋);extract.py 已能真实产候选,写库/审核流在后续 feature。
- 原始 `data/raw/` 保留为备份,可后续清理。
- feat-006 纵切:主图挂 learner_model(SqlLearnerModel 实现 profile()/weak_topics() 读 mastery,record_qa_turn 写 qa_history/mastery);C 检索扩展在 qa_graph.retrieve 用 weak_topics。
- feat-007 训练闭环:`from app.engine.training import SqlTrainingService`;子图 `build_training_graph(training, retriever)`;主图 `build_main_graph(..., training_service=svc)`。出题不足走 LLM 生成(候选落 question_bank,approved_by 空)。交互式:initial_state(..., learner_answer="...") 带作答才批改。
- feat-008 项目里程碑:`from app.engine.capstone import SqlCapstoneService`;子图 `build_capstone_graph(capstone)`;主图 `build_main_graph(..., capstone_service=svc)`。学员自述取 State.query;milestone_progress 状态机 not_started/in_progress/passed 不回退;artifact_summary 存自述(V2 产出物占位)。
- feat-009 教学洞察:`from app.engine.insights import SqlInsightsService`;路由 app/routes/insights.py(prefix /api/insights),已注册进 main.py。GET /courses/{id} 只读聚合、GET /courses/{id}/learners/{id} 个体档案、POST /courses/{id}/mastery-corrections 讲师修正(标 instructor_corrected)。
- feat-010 evals 门禁:数据集 `evals/datasets/qa_quality.json`、判分器 `evals/runner/qa_quality_runner.py`(standalone `main()` 打印 4/4)、pytest 门禁 `tests/test_evals_qa_quality.py`。动态加载 runner 的 dataclass 须先 `sys.modules[spec.name]=mod` 再 `exec_module`,否则 dataclasses 解析报 AttributeError。扩充用例只需往 json 追加 {query, expected_evidence: strong|weak|insufficient, expect_refusal, expect_citation},门禁自动覆盖。
- feat-010(收尾)待做:全量 pytest 已 67 passed/1 skipped(1 skip=真实 Ark embedding 冒烟需 export .env)。需:①校对 init.sh 校验命令与 README/文档;②evals 补拒答与引用正确性用例(可在 tests/ 加或独立 evals 目录);③session-handoff.md 若存在则更新;④跑一次真实 Ark 全链路(问答/训练/项目)冒烟归档。检查 /chat 是否需暴露 E/F(当前仅问答纵切经 HTTP,E/F 经引擎 API+测试验证)。
- 引擎入口:`from app.engine.orchestration import build_main_graph, initial_state`;检索器 `VectorStoreRetriever`;LangGraph checkpointer 可传 SqliteSaver 做会话持久化(build_main_graph 已留 checkpointer 参数)。
- feat-012 训练/项目 HTTP 端点:**直接调引擎**(不经 build_main_graph 图路由),与 insights 一致——`app/routes/training.py`(get_training_service DI 注入 llm,POST /api/training/courses/{id}/questions 出题用 SqlLearnerModel.weak_topics + VectorStoreRetriever,POST .../grade 服务端 `service.get_question(pack_id, qid)` 重载判分)、`app/routes/capstone.py`(GET /api/capstone/courses/{id}/milestones?learner_id= 走 `service.list_milestones`,POST .../{mid}/assess)。**防泄题铁律**:出题/批改响应永不含 reference_answer,批改端点按 question_id 服务端重载,不信任前端回传。新增只读方法只读 CoursePack+业务库,引擎领域无关不变。
- FE-007 学生端训练/项目页:`api/{training,capstone}.ts` + `hooks/{useTraining,useCapstone}.ts` + `routes/{training,capstone}.tsx`;学生身份 `demo_user`(与 chat DEFAULT_USER 一致)。textarea 沿用「Enter 换行、点击按钮提交」防误触纪律。同步等待用 loading/grading/assessing 区分阶段 + Skeleton(非 spinner)。/training、/capstone 已套 RequireRole=student。
- feat-013 项目陪练引导数据〔superseded by feat-014〕:曾把引导内容(overview/background/final_deliverable + 每里程碑 deliverable/hint/sample_report)放课程包透传;sample_report 已随重设计从 manifest 移除(schema 字段保留可选空串向后兼容)。
- FE-008 项目陪练引导 UI〔superseded by FE-009〕:曾在自述判定页加项目说明书 + 范例提交面板;已随自述判定路径一并移除。
- **feat-014 项目陪练重设计(立项向导 + 个性化清单)ADR-0006 铁律**:里程碑序列/名称/交付要求来自课程包,项目卡技术选型由 LLM 依课程包推断,清单绑定到学生自己项目——引擎零课程/项目/技术硬编码。数据流:`persistence.CapstoneProject`(goal/audience/difficulty/card_json/checklist_json)存立项与清单;`SqlCapstoneService.get_project/create_project/toggle_item`。create_project 用 LLM+RAG(retrieve 锚定课程材料)生成项目卡+每里程碑清单,`_parse_llm_json` 失败或 mock/401 时走 `_fallback_items`(按 deliverable 中英文句读拆解,2-4 项/里程碑,离线可跑)。toggle_item `_derive_status` 全勾→PASSED/有勾→IN_PROGRESS/无勾→NOT_STARTED 写回 MilestoneProgress(供教学洞察漏斗)。`_item_id` sha1 稳定 id。业务库无迁移机制,新表 init_business_db 自动建;MilestoneProgress 保持不变。删了 orchestration/subgraphs/capstone_graph.py(/chat 恒走 _stub,无回归)。
- FE-009 项目陪练重设计前端:`api/client.ts` 加 `apiPatch`;`api/capstone.ts` getProject/createProject/toggleItem;`api/types.ts` ProjectCard/ChecklistItemView/ProjectMilestone/CapstoneProjectResponse/CreateProjectRequest/ToggleItemRequest(snake_case 对齐);`hooks/useCapstone` {data,loading,error,reload,create,creating,toggle}(toggle 乐观更新失败回滚);`routes/capstone.tsx` !has_project→ProjectBrief+KickoffWizard(三 textarea,goal 必填,点击提交非回车),has_project→进度总览+项目卡(Compass/Stack/Badge accent 技术选型)+每里程碑 MilestoneCard(checkbox 清单 accent 色)。/capstone 仍 RequireRole=student。
- **下一迭代重点(用户反馈)**:立项向导已让学生用自己的项目上手;进一步可做可跟随的 demo 引导流。
- **feat-015 学生登录与学习者身份(后端,ADR-0008)**:轻量账号——`persistence.LearnerAuth`(learner_id PK/FK、username unique-index、password_hash、created_at)+ `LearnerProfile`(nickname/avatar/background/learning_goal/weekly_hours/preferred_difficulty/updated_at);业务库 create_all 自动建,非破坏。`app/auth/`:security.py(bcrypt hash/verify + stdlib hmac/hashlib/base64 自签 token,格式 `b64url(payload).b64url(sig)`,payload 含 learner_id/username/exp,**不引 JWT 库**)、service.py(AuthService/AuthError,learner_id=`stu_<username>`,register/login/get_account/update_profile 白名单/auto_profile 聚合 Mastery known/fuzzy/unknown/topics_tracked;用户名正则 2-32 位字母数字下划线中文、密码≥6)、deps.py(current_learner_id 从 Authorization 头解析、`resolve_learner_id(fallback, authorization, settings)` token 身份优先否则回退)。config 加 `auth_token_secret`(AUTH_TOKEN_SECRET,dev 占位)+ `auth_token_ttl_hours`(AUTH_TOKEN_TTL_HOURS,默认 168)。routes/auth.py prefix `/api/auth`(POST /register 422、POST /login 401、GET/PATCH /me 需 token 401/404),main.py 注册。**身份接入**:chat/training/capstone 路由加 resolve_learner_id,chat 从 Authorization 头解析一次 user_id 复用(会话库+trace+图 learner_id),list_conversations 亦解析——**token 身份覆盖请求体**,无 token 走访客 `demo_user`。`stu_<username>` 与 demo_user 数据天然隔离。无 CORS(dev 走 Vite proxy 同源)。⚠️ 生产必须覆盖 AUTH_TOKEN_SECRET。
- **FE-010 学生登录与画像 UI(前端,ADR-0008)**:`lib/auth.tsx` AuthProvider+useAuth()(session/learnerId/isAuthed/signIn/signOut,localStorage key `ai-tutor-auth`,GUEST_LEARNER_ID=demo_user,`getStoredToken()` 供非组件模块);`api/client.ts` buildHeaders 从 getStoredToken 注入 `Authorization: Bearer`(未登录不带头走访客);`api/auth.ts`(register/login/fetchAccount/updateProfile)+ types 追加 auth schema;`main.tsx` 挂 AuthProvider(ThemeProvider 内 RoleProvider 外)。`ui/input.tsx`(token 化单行输入);`routes/login.tsx`(登录/注册切换,点击提交非回车,成功 signIn 跳 /student,提示可访客体验);`routes/profile.tsx`(需登录否则 Navigate /login;基础资料/学习目标偏好可编辑+自动画像只读徽章;PATCH /me;退出登录)。App.tsx 加 /login、/profile(无 RequireRole,面向未登录学生);AppShell 学生态登录按钮(未登录)或用户名+我的画像入口+退出图标(已登录),讲师态不显示。**useCapstone/useTraining 用 useAuth().learnerId 取代 demo_user 常量**(加入 effect/callback deps);chat.ts DEFAULT_USER 保留(后端 token 覆盖身份)。typecheck/lint(--max-warnings 0)/build 三关零告警。
- **feat-024 教师端学员列表 + 学员存在性校验(修复假存在)**:修复用户反馈的两处关联缺陷——教师端无学员列表(teacher.tsx 原自标「下一迭代」只留手输 ID 框)、`learner_profile` 从不校验 Learner 存在导致任意字符串返回空档案+HTTP 200 假装存在(违反诚实铁律)。后端 `SqlInsightsService.learner_profile` 先查 `Learner` 表,不存在抛 `LearnerNotFoundError`→路由 `try/except`→404;新增 `list_learners(course_pack_id,limit,offset)` 分页聚合每人课程包内 known/fuzzy/unknown 概览(掌握数降序→learner_id 升序稳定分页,limit clamp 1-100),`GET /api/insights/courses/{id}/learners`(require_teacher,Query ge/le 约束);schema +`LearnerListItem/LearnerListResponse`;`__init__` 导出异常。前端 `useLearners` hook(四态+分页+reload+AbortController)+ `LearnerList` 组件(点选打开现有 LearnerDrawer、known/fuzzy/unknown 徽章、上下页),`teacher.tsx` 用列表替换占位卡、手输框保留为辅助、`LearnerDrawer` 遇不存在 ID 现走 404 error 态(不再假装存在)。**铁律遵守**:改动仅在洞察(T)纵切,掌握度计数只认注入 CoursePack 的 topic_ids,引擎领域无关不变。验证:pytest 159 passed/1 skipped(+5 用例);eval 4/4;前端 typecheck/lint(--max-warnings 0)/vitest 8/build 全绿;真实后端重启后 E2E:learners→200 带真实账号+计数+分页、ghost 档案→404 learner_not_found、无 token→401。⚠️ 注意 uvicorn 无 --reload,改后端后须重启进程才生效(本次首测命中旧进程,重启后通过)。

- **feat-024 追加修复(用户提问「学员 id 是不是昵称前加 tea」暴露)**:学员 id 规则在 `app/auth/service.py`——学生 `stu_<username>`、讲师 `tea_<username>`(STUDENT_PREFIX/TEACHER_PREFIX,`_learner_id_for`)。原 `list_learners` 查全部 `Learner` 行,而注册讲师也会写一行 `Learner`(id 为 `tea_` 前缀),导致讲师被错误列为学员。修复:`list_learners` 的 total 计数与列表查询均按 `Learner.learner_id.startswith(STUDENT_PREFIX)` 过滤,仅列学生;讲师个体档案不受影响(仍可按精确 id 查)。测试 `test_insights.py` 两处 list 用例改播种 stu_/tea_ 前缀并断言讲师被排除(`_seed()` 仍用无前缀 u0/u1/u2 供其他精确查询用例,未动)。重跑 pytest 159 passed/1 skipped、eval 4/4、前端三关全绿;E2E 确认仅注册讲师时 learners 列表为空,注册学生 alice 后仅显示 stu_alice。

- **feat-024 再追加修复(用户「学员数量统计也有问题」)**:同根因——`course_insights.learner_count` 与 `north_star_metrics.active_learners` 原也 COUNT 全部 `Learner` 行,讲师(tea_ 前缀)被计入使学员数虚高。两处 COUNT 均加 `Learner.learner_id.startswith(STUDENT_PREFIX)` 过滤,仅计学生。其余聚合(掌握度/做题/里程碑/问答)按 topic_id、course_pack_id 或具体数据行统计,讲师无这些数据不污染,但学员计数统一到 stu_ 口径。测试:`test_insights.py`/`_seed` 与 `test_metrics.py`/`_seed` 播种 id 由 u0/u1/u2 改为 stu_0/1/2(精确查询用例同步),新增 `test_learner_count_excludes_teachers`(播种 tea_prof 后断言两处计数仍=3)。重跑 pytest 160 passed/1 skipped、eval 4/4、前端三关全绿;E2E(讲师 tea_demo + 学生 stu_alice)course_insights.learner_count=1、north_star active_learners=1。

- **feat-025 训练「换一题」真正换题(修复恒定同题)**:用户反馈学生端训练点「换一题」无效果、始终同一道。根因两点叠加——新学员无掌握度→weak_topics 空→出题知识点恒取 taxonomy 首个;同知识点内防重复轮换只看 ExerciseAttempt,而「换一题」不作答不产生 attempt→counts 恒空→每次 bucket[0] 同题。修复:引入 exclude_ids——前端 useTraining 用 useRef 记录本轮已见题 id 并回传,后端 select_question 先跳过已见题,当前知识点耗尽则按 _ordered_topics(薄弱优先+补齐 taxonomy)轮换下一知识点,全排除才 LLM 生成,真耗尽回退旧题。删 _pick_target_topic 换成 _ordered_topics。测试 test_training_enhancements.py +2(同知识点连换不同题、耗尽轮换下一知识点)。pytest 162 passed/1 skipped、eval 4/4、前端三关全绿;E2E:连续换题依次 agent_basics easy/medium/hard 三题后自动换到 tools 知识点。铁律:知识点顺序与选题只由注入 CoursePack/taxonomy/题库决定,引擎领域无关不变。⚠️ uvicorn 无 --reload,改后端须重启。
