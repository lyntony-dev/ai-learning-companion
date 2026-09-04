import { apiGet, apiPost } from './client';
import type {
  CourseInsightsResponse,
  LearnerListResponse,
  LearnerProfileResponse,
  MasteryCorrectionRequest,
  MasteryCorrectionResponse,
  NorthStarMetricsResponse,
} from './types';

export const DEFAULT_COURSE_PACK = 'ai_agent';

export function getCourseInsights(
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<CourseInsightsResponse> {
  return apiGet<CourseInsightsResponse>(
    `/insights/courses/${encodeURIComponent(coursePackId)}`,
    signal,
  );
}

/** 北极星指标(讲师只读):活跃/诚实拒答率/掌握进度/练习质量/结课漏斗。需讲师身份。 */
export function getNorthStarMetrics(
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<NorthStarMetricsResponse> {
  return apiGet<NorthStarMetricsResponse>(
    `/insights/courses/${encodeURIComponent(coursePackId)}/metrics`,
    signal,
  );
}

export function getLearnerProfile(
  learnerId: string,
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<LearnerProfileResponse> {
  return apiGet<LearnerProfileResponse>(
    `/insights/courses/${encodeURIComponent(coursePackId)}/learners/${encodeURIComponent(learnerId)}`,
    signal,
  );
}

/** 学员列表(讲师只读,分页)。每人带课程包知识点掌握度概览计数。需讲师身份。 */
export function listLearners(
  coursePackId: string = DEFAULT_COURSE_PACK,
  limit = 20,
  offset = 0,
  signal?: AbortSignal,
): Promise<LearnerListResponse> {
  const qs = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return apiGet<LearnerListResponse>(
    `/insights/courses/${encodeURIComponent(coursePackId)}/learners?${qs.toString()}`,
    signal,
  );
}

/**
 * 讲师修正掌握度。均需讲师身份(无 token→401,非讲师→403);
 * updated_by 以认证讲师身份为准(不再由前端传);topic 越界→422;课程包不存在→404。
 */
export function correctMastery(
  req: MasteryCorrectionRequest,
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<MasteryCorrectionResponse> {
  return apiPost<MasteryCorrectionResponse>(
    `/insights/courses/${encodeURIComponent(coursePackId)}/mastery-corrections`,
    req,
    signal,
  );
}
