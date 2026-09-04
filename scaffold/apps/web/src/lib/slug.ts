/**
 * 标题 slug 生成 (CoursewareDoc v1)。
 *
 * 必须与后端 apps/api/app/course_pack/slug.py 行为对齐,课件锚点跳转才不漂移。
 * 规则:小写 → 去首尾空白 → 非(字母/数字/中文)转 '-' → 合并连续 '-' → 去首尾 '-'。
 * 教师可用标题后缀 `{#custom-anchor}` 显式覆盖。
 */

// 保留 ASCII 字母数字 + 中文(基本区),其余转连字符。
const KEEP = /[^0-9a-z\u4e00-\u9fff]+/g;
const EXPLICIT = /\{#([0-9a-zA-Z\u4e00-\u9fff\-_]+)\}\s*$/;

export function slugify(text: string): string {
  let s = text.trim().toLowerCase();
  s = s.replace(KEEP, '-');
  s = s.replace(/^-+/, '').replace(/-+$/, '');
  return s;
}

/** 从标题剥离 `{#anchor}`。返回 [清洗后的文本, 显式锚点或 null]。 */
export function extractExplicitAnchor(heading: string): [string, string | null] {
  const m = EXPLICIT.exec(heading);
  if (!m) return [heading.trim(), null];
  return [heading.slice(0, m.index).trim(), m[1]];
}

/** 给标题算最终 [显示文本, anchor]。显式锚点优先,否则 slug。 */
export function headingAnchor(heading: string): [string, string] {
  const [clean, explicit] = extractExplicitAnchor(heading);
  return [clean, explicit ?? slugify(clean)];
}
