import { apiGet } from './client';
import type { LearningArchiveResponse } from './types';

export const DEFAULT_COURSE_PACK = 'ai_agent';

/**
 * 我的学习档案(Tier 2-6):本人本课程包的掌握度 / 练习 / 项目进度聚合。
 * 强制登录;learner_id 由后端从 token 解析,只读自己数据(不接受他人 id)。
 * 未登录 → 401;课程包不存在 → 404。
 */
export function fetchLearningArchive(
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<LearningArchiveResponse> {
  return apiGet<LearningArchiveResponse>(
    `/archive/courses/${encodeURIComponent(coursePackId)}`,
    signal,
  );
}
