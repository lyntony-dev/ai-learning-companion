# ADR-0008：学生登录与学习者身份——轻量账号 + 访客兜底

- 状态：已接受
- 日期：2026-07-20

## 背景

此前应用是无状态的：所有学生请求硬编码为 `demo_user`，无法区分不同学生，也无法长期累积/更新每个学生的画像信息（背景、学习目标、掌握进度）。用户要求在学生端加入登录功能，让每个学生拥有独立、可持久化的身份与画像。

约束与取向（用户确认）：

- **轻量优先**，不过度设计：用户名 + 密码即可，不引入 PyJWT / passlib 等重依赖（bcrypt 已在依赖内）。
- **访客兜底**：`demo_user` 必须继续作为可用的访客身份，未登录仍能"打开即用"，登录不得破坏体验。
- 画像需覆盖三组信息：**基础资料**（昵称/头像/背景）、**学习目标偏好**（目标/每周投入/偏好难度）、**自动画像**（依训练与作答自动统计，只读）。

候选：A 引入 OAuth / 第三方登录（MVP 过重、依赖外部）；B 轻量自建账号 + HMAC 签名 token + 访客兜底（采纳）；C 无账号、仅设备本地 id（无法跨设备、无凭据保护）。

## 决策

- **凭据与身份**：新增两张业务表(`create_all`，非破坏)：
  - `learner_auth(learner_id PK/FK, username unique, password_hash, created_at)`：密码用 **bcrypt** 哈希。
  - `learner_profile(learner_id PK/FK, nickname, avatar, background, learning_goal, weekly_hours, preferred_difficulty, updated_at)`。
  - `learner_id` 规则 = `stu_<username>`，与访客 `demo_user` 数据天然隔离。
- **Token**：不引 JWT 库，用 stdlib `hmac`/`hashlib`/`base64` 自签，格式 `b64url(payload).b64url(sig)`，payload 含 `learner_id/username/exp`；密钥与 TTL 走 `config.py`（`AUTH_TOKEN_SECRET` 默认 dev 占位、`AUTH_TOKEN_TTL_HOURS` 默认 168h）。
- **身份解析(`resolve_learner_id`)**：Authorization 头带有效 token 时身份以 token 为准；否则回退到请求体的 `user_id`/`learner_id`（默认 `demo_user`）。chat / capstone / training 路由统一走此解析——**token 身份覆盖请求体**，访客无 token 仍可用。
- **接口**：`/api/auth` 下 `POST /register`(422 业务错)、`POST /login`(401)、`GET /me` + `PATCH /me`(需 token,401/404)。
- **前端**：`AuthProvider` + `useAuth()`(localStorage `ai-tutor-auth` 持久化,刷新恢复)；`getStoredToken()` 供 api client 注入 `Authorization`；`/login`(登录/注册切换)、`/profile`(三组画像,自动画像只读)；AppShell 学生态显示登录按钮 / 用户菜单。

## 权衡

- **成本**：自签 token 无吊销/刷新机制，密钥泄露即可伪造；bcrypt 无盐轮次配置暴露。MVP 可接受，V2 可平滑换 JWT + 刷新。
- **收益**：零新增重依赖；访客态零回归;画像与掌握度按真实 `learner_id` 沉淀,为教学洞察 per-learner 聚合打基础。
- **被否决**：A(OAuth,MVP 过重);C(仅设备 id,无凭据、不能跨设备)。

## 影响

- 业务库新增两表（`create_all`,无迁移/ALTER,非破坏）。
- 生产部署必须覆盖 `AUTH_TOKEN_SECRET`，dev 默认值仅供本地。
- 无 CORS 变更（dev 经 Vite proxy 同源）。
- ADR-0006 关于 capstone 引擎领域无关的铁律不受影响。
