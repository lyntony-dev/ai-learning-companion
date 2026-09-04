import { apiGet, apiPatch, apiPost } from './client';
import type {
  CapstoneProjectResponse,
  CreateProjectRequest,
  ToggleItemRequest,
} from './types';

export const DEFAULT_COURSE_PACK = 'ai_agent';

/** 读项目状态:未立项 → 向导态(has_project=false),已立项 → 项目卡 + 个性化清单。 */
export function getProject(
  learnerId: string,
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<CapstoneProjectResponse> {
  return apiGet<CapstoneProjectResponse>(
    `/capstone/courses/${encodeURIComponent(coursePackId)}/project?learner_id=${encodeURIComponent(learnerId)}`,
    signal,
  );
}

/** 立项:提交想法(goal/audience/difficulty),后端用 LLM+RAG 生成项目卡与每里程碑清单。 */
export function createProject(
  req: CreateProjectRequest,
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<CapstoneProjectResponse> {
  return apiPost<CapstoneProjectResponse>(
    `/capstone/courses/${encodeURIComponent(coursePackId)}/project`,
    req,
    signal,
  );
}

/** 勾选/取消一条清单项;里程碑状态由勾选完成度派生。清单项不存在 → 404。 */
export function toggleItem(
  itemId: string,
  req: ToggleItemRequest,
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<CapstoneProjectResponse> {
  return apiPatch<CapstoneProjectResponse>(
    `/capstone/courses/${encodeURIComponent(coursePackId)}/project/items/${encodeURIComponent(itemId)}`,
    req,
    signal,
  );
}
