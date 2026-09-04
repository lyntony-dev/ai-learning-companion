# ADR-0009：讲师端鉴权与角色权限——堵住教学洞察安全缺口

- 状态：已接受
- 日期：2026-07-26

## 背景

ADR-0008 只给**学生**做了轻量登录。讲师端(教学洞察 `/api/insights/*`)一直是 **demo 无鉴权**状态：

- 后端三端点(per-course 聚合、个体档案、讲师修正掌握度)没有任何身份校验,`learner_id` 只是路径参数——任何人都能拉全班学情、甚至替讲师改掌握度。
- 前端 `RoleSwitcher` 允许任何访客一键切成"讲师"视图,是同一缺口的前端侧。
- 掌握度修正的 `updated_by` 由请求体自报,可伪造。

这与 VISION「两类一等公民(学员 + 讲师)」直接冲突,是发布前必须堵的安全硬缺口,非 V2 可选项。

## 决策

复用 ADR-0008 的轻量 auth 基座,不引新依赖、不做业务库迁移:

- **角色载入 token**:`sign_token` 增加 `role` 字段(缺省 `student`,兼容旧 token)。讲师 `learner_id = tea_<username>`,学生 `stu_<username>`;`role_of(learner_id)` 由前缀派生作兜底。角色**不落库**(业务库无迁移机制),纯由 token 携带 + 前缀派生。
- **讲师注册需邀请码**:讲师账号非自由注册,`register(role="teacher", invite_code=...)` 校验 `AUTH_TEACHER_INVITE_CODE`(config,dev 占位 `dev-teacher-invite`,生产必须覆盖,同 `AUTH_TOKEN_SECRET`)。
- **端点守卫**:新增 `require_teacher` 依赖(无 token→401,非讲师→403);`/api/insights/*` 三端点全部挂载。
- **防伪造**:掌握度修正的 `updated_by` 以**认证讲师身份**为准(取 token 内 username),忽略请求体字段(保留字段仅向后兼容)。
- **前端角色由真实身份派生**:删除 demo `RoleSwitcher`;`useRole()` 改为从 `useAuth().session.role` 派生。讲师账号登录后见教学洞察,学生/访客只见学生态。`/teacher` 路由守卫:未登录跳 `/login`。登录页增加学生/讲师注册切换 + 讲师邀请码输入。

候选:A 引入完整 RBAC/权限表(MVP 过重);B token 携带角色 + 前缀约定 + 邀请码门槛(采纳,零迁移、零新依赖);C 仅前端隐藏讲师入口(治标不治本,后端仍敞开)。

## 影响

- **正面**:堵住越权读写全班学情的安全缺口;讲师身份可鉴别、可审计(`updated_by` 真实);访客/学生态零回归(未登录仍可用学生功能)。
- **代价/风险**:
  - 角色不落库,靠 token 前缀约定——够 MVP,但改角色需重签 token;若未来要「一人多角色」或「撤销讲师权限」需升级为角色表。
  - 邀请码是单一共享秘密,非按人分发;⚠️ 生产必须覆盖 `AUTH_TEACHER_INVITE_CODE` 与 `AUTH_TOKEN_SECRET`。
  - 自签 token 仍无吊销/刷新(承 ADR-0008 遗留),V2 可平滑换 JWT + 刷新 + 角色表。

## 验证

- 后端 `pytest`:`test_auth_api.py` 补讲师注册需邀请码/登录带 role/学生打洞察 403/无 token 401/讲师可访问;`test_insights.py` 全部 HTTP 用例改带讲师 token,补 401/403 与「updated_by 以认证讲师为准」断言。全量 `119 passed, 1 skipped`,eval `4/4`。
- 前端 typecheck/lint/build 三关零告警。
