/**
 * API 类型:逐字段对齐后端 Pydantic schema(snake_case),不做命名转换,
 * 避免映射漂移。来源见 apps/api/app/schemas/{chat,insights}.py。
 */

/* ============ 通用 ============ */

export type MasteryLevel = 'known' | 'fuzzy' | 'unknown';
export type MasterySource = 'system_inferred' | 'instructor_corrected';

/* ============ 问答 /api/chat ============ */

export interface ChatRequest {
  question: string;
  conversation_id?: string | null;
  user_id?: string;
  course_ids?: string[];
  top_k?: number;
}

export interface Citation {
  citation_id: number;
  chunk_id: string;
  course_id: string;
  course_name: string;
  section: string;
  source_path: string;
  slide_no: number | null;
  /** 引用定位单元类型 (CoursewareDoc v1):heading | slide | page | none */
  anchor_type?: string;
  /** 定位值:heading→slug,slide/page→页码字符串 */
  anchor_value?: string;
}

export interface AgentTraceEvent {
  node_name: string;
  status: string;
  input_summary: string;
  output_summary: string;
  metadata: Record<string, string | number | boolean | null>;
}

/** status: "insufficient"(拒答)| 证据等级 "strong" | "weak" */
export interface ChatResponse {
  conversation_id: string;
  trace_id: string;
  answer: string;
  status: string;
  citations: Citation[];
  trace: AgentTraceEvent[];
}

export interface ConversationSummary {
  conversation_id: string;
  user_id: string;
  title: string;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
}

export interface MessageSummary {
  message_id: string;
  conversation_id: string;
  role: string;
  content_summary: string;
  /** 全文(002 起);历史恢复优先用它,回退 content_summary。 */
  content?: string | null;
  /** 关联本轮 trace(仅 assistant),用于历史 Agent Trace 懒加载。 */
  trace_id?: string | null;
  citations: Array<Record<string, string | number | null>>;
}

export interface MessageListResponse {
  messages: MessageSummary[];
}

export interface TraceEventSummary {
  event_id: string;
  trace_id: string;
  node_name: string;
  status: string;
  latency_ms: number;
  input_summary: string;
  output_summary: string;
  metadata: Record<string, string | number | boolean | null>;
}

export interface TraceResponse {
  trace_id: string;
  events: TraceEventSummary[];
}

/* ============ 课程浏览 /api/courses ============ */

/** kind: lecture_note | slide | code_example | attachment;rel_path 相对 materials/ */
export interface MaterialRef {
  kind: string;
  title: string;
  rel_path: string;
}

/** 课件内可寻址段(标题 → 锚点),供学生端目录跳转 (CoursewareDoc v1) */
export interface CoursewareSection {
  anchor: string;
  title: string;
}

/** 结构化课件。rel_path 相对 courseware/ */
export interface CoursewareRef {
  rel_path: string;
  title: string;
  sections: CoursewareSection[];
}

export interface CourseSummary {
  course_id: string;
  name: string;
  /** 有结构化课件时为主体;原始资料降为 materials(附件) */
  courseware?: CoursewareRef | null;
  materials: MaterialRef[];
}

export interface CoursePackSummary {
  course_pack_id: string;
  name: string;
  description: string;
  version: string;
  course_count: number;
}

export interface CoursePackListResponse {
  packs: CoursePackSummary[];
}

export interface CoursePackDetailResponse {
  course_pack_id: string;
  name: string;
  description: string;
  version: string;
  courses: CourseSummary[];
}

/* ============ 教学洞察 /api/insights ============ */

export interface TopicInsight {
  topic_id: string;
  name: string;
  course_id: string;
  known: number;
  fuzzy: number;
  unknown: number;
  attempts: number;
  avg_score: number | null;
}

export interface MilestoneInsight {
  milestone: string;
  not_started: number;
  in_progress: number;
  passed: number;
}

export interface CourseInsightsResponse {
  course_pack_id: string;
  learner_count: number;
  topics: TopicInsight[];
  weak_ranking: TopicInsight[];
  milestones: MilestoneInsight[];
}

export interface MasteryEntry {
  topic_id: string;
  name: string;
  level: string;
  source: string;
  updated_by: string;
}

export interface LearnerProfileResponse {
  learner_id: string;
  course_pack_id: string;
  masteries: MasteryEntry[];
}

export interface LearnerListItem {
  learner_id: string;
  display_name: string;
  known: number;
  fuzzy: number;
  unknown: number;
  tracked_topics: number;
}

export interface LearnerListResponse {
  course_pack_id: string;
  items: LearnerListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface MasteryCorrectionRequest {
  learner_id: string;
  topic_id: string;
  level: MasteryLevel;
  /** 已忽略:后端以认证讲师身份为准(保留字段向后兼容) */
  updated_by?: string;
}

export interface MasteryCorrectionResponse {
  learner_id: string;
  topic_id: string;
  level: string;
  source: string;
  updated_by: string;
}

/* 北极星指标 /api/insights/courses/{id}/metrics(Tier 3-7)。来源见 schemas/insights.py。 */

export interface MetricsEngagement {
  active_learners: number;
  qa_turns: number;
  practice_attempts: number;
}

export interface MetricsHonesty {
  qa_turns: number;
  refused: number;
  refusal_rate: number;
}

export interface MetricsMasteryProgress {
  topics_tracked: number;
  known: number;
  known_rate: number;
}

export interface MetricsPracticeQuality {
  attempts: number;
  avg_score: number | null;
}

export interface MetricsCapstoneFunnel {
  kickoff: number;
  completed: number;
  completion_rate: number;
}

export interface NorthStarMetricsResponse {
  course_pack_id: string;
  engagement: MetricsEngagement;
  honesty: MetricsHonesty;
  mastery_progress: MetricsMasteryProgress;
  practice_quality: MetricsPracticeQuality;
  capstone_funnel: MetricsCapstoneFunnel;
}

/* ============ 训练闭环 /api/training ============ */
/* 来源见 apps/api/app/schemas/training.py。响应永不含 reference_answer(防泄题)。 */

export interface QuestionRequest {
  learner_id?: string;
  /** 「换一题」时回传本轮已展示过的题目 id,后端选题会跳过它们。 */
  exclude_ids?: string[];
}

export interface TrainingQuestion {
  question_id: string;
  topic_id: string;
  topic_name: string;
  prompt: string;
  source: string;
  /** 难度:easy | medium | hard(自适应出题,前端显示难度徽标) */
  difficulty?: string;
  /** 无可练知识点时为 true,前端展示空态 */
  empty: boolean;
}

export interface GradeRequest {
  learner_id?: string;
  question_id: string;
  answer: string;
}

export interface GradeDimension {
  key: string;
  name: string;
  weight: number;
  score: number;
}

export interface MasteryUpdate {
  topic_id: string;
  level: string;
  overwritten: boolean;
}

export interface GradeResponse {
  question_id: string;
  topic_id: string;
  score: number;
  passed: boolean;
  feedback: string;
  dimensions: GradeDimension[];
  mastery: MasteryUpdate;
}

/* 讲师审核沉淀(candidate → approved / rejected,ADR-0006 飞轮)。仅经讲师守卫路由。 */

export interface CandidateQuestion {
  question_id: string;
  topic_id: string;
  topic_name: string;
  prompt: string;
  /** 参考答案:仅讲师审核态可见(学生端出题/批改不含) */
  reference_answer: string;
  difficulty?: string;
  source: string;
  created_at: string;
}

export interface CandidateQuestionList {
  course_pack_id: string;
  candidates: CandidateQuestion[];
}

export interface ApproveQuestionResponse {
  question_id: string;
  topic_id: string;
  approved_by: string;
}

export interface RejectQuestionResponse {
  question_id: string;
  rejected: boolean;
}

/* ============ 我的学习档案 /api/archive(Tier 2-6)============ */
/* 来源见 apps/api/app/schemas/archive.py。学生登录态自查本人学习轨迹。 */

export interface ArchiveMastery {
  topic_id: string;
  name: string;
  level: string; // known | fuzzy | unknown
  source: string; // system_inferred | instructor_corrected
}

export interface ArchiveLevels {
  known: number;
  fuzzy: number;
  unknown: number;
}

export interface ArchiveRecentAttempt {
  topic_id: string;
  name: string;
  score: number;
  created_at: string;
}

export interface ArchivePractice {
  attempts: number;
  avg_score: number | null;
  recent: ArchiveRecentAttempt[];
}

export interface ArchiveMilestone {
  milestone_id: string;
  status: string; // not_started | in_progress | passed
}

export interface ArchiveCapstone {
  has_project: boolean;
  goal: string;
  passed: number;
  total: number;
  milestones: ArchiveMilestone[];
}

export interface LearningArchiveResponse {
  learner_id: string;
  course_pack_id: string;
  levels: ArchiveLevels;
  topics_tracked: number;
  masteries: ArchiveMastery[];
  practice: ArchivePractice;
  capstone: ArchiveCapstone;
}

/* ============ 结课项目 /api/capstone ============ */
/* 来源见 apps/api/app/schemas/capstone.py。立项向导 + 个性化清单。 */

export interface ProjectCard {
  title: string;
  scope: string;
  tech_stack: string[];
}

export interface ChecklistItemView {
  id: string;
  text: string;
  checked: boolean;
}

export interface ProjectMilestone {
  milestone_id: string;
  name: string;
  status: string; // not_started | in_progress | passed
  deliverable: string;
  hint: string;
  items: ChecklistItemView[];
}

export interface CapstoneProjectResponse {
  course_pack_id: string;
  capstone_name: string;
  has_project: boolean;
  card: ProjectCard | null;
  milestones: ProjectMilestone[];
  current_milestone_id: string;
  passed_count: number;
  total: number;
  all_passed: boolean;
  overview: string;
  background: string;
  final_deliverable: string;
}

export interface CreateProjectRequest {
  learner_id?: string;
  goal: string;
  audience?: string;
  difficulty?: string;
}

export interface ToggleItemRequest {
  learner_id?: string;
  checked: boolean;
}

/* ============ 登录 / 画像 /api/auth(ADR-0008)============ */

export interface RegisterRequest {
  username: string;
  password: string;
  display_name?: string;
  role?: 'student' | 'teacher';
  invite_code?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface AuthTokenResponse {
  learner_id: string;
  username: string;
  display_name: string;
  role: 'student' | 'teacher';
  token: string;
}

export interface ProfileFields {
  nickname: string;
  avatar: string;
  background: string;
  learning_goal: string;
  weekly_hours: number;
  preferred_difficulty: string;
}

export interface AutoProfile {
  known: number;
  fuzzy: number;
  unknown: number;
  topics_tracked: number;
}

export interface AccountResponse {
  learner_id: string;
  username: string;
  display_name: string;
  role: 'student' | 'teacher';
  profile: ProfileFields;
  auto_profile: AutoProfile;
}

export type UpdateProfileRequest = Partial<{
  nickname: string;
  avatar: string;
  background: string;
  learning_goal: string;
  weekly_hours: number;
  preferred_difficulty: string;
}>;
