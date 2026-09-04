import { apiGet, ApiError } from './client';
import type { CoursePackDetailResponse, CoursePackListResponse } from './types';

export const DEFAULT_COURSE_PACK = 'ai_agent';

export function listCoursePacks(signal?: AbortSignal): Promise<CoursePackListResponse> {
  return apiGet<CoursePackListResponse>('/courses', signal);
}

export function getCoursePack(
  coursePackId: string = DEFAULT_COURSE_PACK,
  signal?: AbortSignal,
): Promise<CoursePackDetailResponse> {
  return apiGet<CoursePackDetailResponse>(`/courses/${encodeURIComponent(coursePackId)}`, signal);
}

/**
 * 资料文件直链(iframe/embed 内联渲染:HTML PPT、PDF)。
 * rel_path 相对课程包 materials/,与引用来源 source_path 同一命名空间。
 */
export function materialUrl(coursePackId: string, relPath: string): string {
  const encoded = relPath
    .split('/')
    .map((seg) => encodeURIComponent(seg))
    .join('/');
  return `/api/courses/${encodeURIComponent(coursePackId)}/materials/${encoded}`;
}

/** 结构化课件正文直链(相对 courseware/)。CoursewareDoc v1 学生端主体。 */
export function coursewareUrl(coursePackId: string, relPath: string): string {
  const encoded = relPath
    .split('/')
    .map((seg) => encodeURIComponent(seg))
    .join('/');
  return `/api/courses/${encodeURIComponent(coursePackId)}/courseware/${encoded}`;
}

/** 按预览目标类型(材料 / 课件)解析内容直链。 */
export function contentUrl(
  coursePackId: string,
  relPath: string,
  kind: 'material' | 'courseware' = 'material',
): string {
  return kind === 'courseware'
    ? coursewareUrl(coursePackId, relPath)
    : materialUrl(coursePackId, relPath);
}

/** 应用内预览的渲染方式:iframe(html/pdf)、markdown、code(py/txt)。 */
export type PreviewKind = 'iframe' | 'markdown' | 'code';

/** 按 rel_path 后缀判定预览渲染方式。 */
export function previewKind(relPath: string): PreviewKind {
  const ext = relPath.slice(relPath.lastIndexOf('.')).toLowerCase();
  if (ext === '.html' || ext === '.htm' || ext === '.pdf') return 'iframe';
  if (ext === '.md') return 'markdown';
  return 'code';
}

/** 拉取文本类内容(markdown / code)。html、pdf 走直连 iframe。 */
export async function fetchContentText(
  coursePackId: string,
  relPath: string,
  kind: 'material' | 'courseware' = 'material',
  signal?: AbortSignal,
): Promise<string> {
  const res = await fetch(contentUrl(coursePackId, relPath, kind), {
    method: 'GET',
    signal,
  });
  if (!res.ok) {
    throw new ApiError(res.status, `content_fetch_failed: ${relPath}`);
  }
  return res.text();
}
