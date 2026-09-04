import { apiGet, apiPost } from './client';
import type {
  ApproveQuestionResponse,
  CandidateQuestionList,
  GradeRequest,
  GradeResponse,
  QuestionRequest,
  RejectQuestionResponse,
  TrainingQuestion,
} from './types';

export const DEFAULT_COURSE_PACK = 'ai_agent';

/** 出题:匹配薄弱知识点(无则退到首个知识点)。响应不含参考答案。 */
export function fetchQuestion(
  req: QuestionRequest,
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<TrainingQuestion> {
  return apiPost<TrainingQuestion>(
    `/training/courses/${encodeURIComponent(coursePackId)}/questions`,
    req,
    signal,
  );
}

/**
 * 批改:服务端按 question_id 重载完整题目(含参考答案)后打分并更新掌握度。
 * question_id 不存在 → 404;课程包不存在 → 404。
 */
export function gradeAnswer(
  req: GradeRequest,
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<GradeResponse> {
  return apiPost<GradeResponse>(
    `/training/courses/${encodeURIComponent(coursePackId)}/grade`,
    req,
    signal,
  );
}

/* --- 讲师审核沉淀(candidate → approved / rejected,需讲师身份)--- */

/** 列出待审核候选题(LLM 生成、未审核)。含参考答案,仅讲师可见。 */
export function fetchCandidates(
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<CandidateQuestionList> {
  return apiGet<CandidateQuestionList>(
    `/training/courses/${encodeURIComponent(coursePackId)}/candidates`,
    signal,
  );
}

/** 通过候选题:沉淀为优先出题来源(approved_by 由后端按认证讲师派生)。 */
export function approveCandidate(
  questionId: string,
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<ApproveQuestionResponse> {
  return apiPost<ApproveQuestionResponse>(
    `/training/courses/${encodeURIComponent(coursePackId)}/candidates/${encodeURIComponent(
      questionId,
    )}/approve`,
    {},
    signal,
  );
}

/** 驳回候选题:删除该候选。 */
export function rejectCandidate(
  questionId: string,
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<RejectQuestionResponse> {
  return apiPost<RejectQuestionResponse>(
    `/training/courses/${encodeURIComponent(coursePackId)}/candidates/${encodeURIComponent(
      questionId,
    )}/reject`,
    {},
    signal,
  );
}
