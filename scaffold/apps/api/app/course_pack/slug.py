"""标题 slug 生成 (CoursewareDoc v1)。

课件正文的每个标题即一个可寻址单元(anchor),anchor = 标题 slug。
后端(摄取/引用)与前端(渲染/跳转)必须用同一套规则,跳转才不漂移。
前端对应实现见 apps/web/src/lib/slug.ts,行为须与本文件对齐。

规则:
  1. 小写
  2. 去首尾空白
  3. 非「字母/数字/中文」字符一律替换为 '-'
  4. 合并连续 '-'
  5. 去首尾 '-'

教师可用 Markdown 标题后缀 `{#custom-anchor}` 显式覆盖(见 extract_explicit_anchor)。
"""

from __future__ import annotations

import re

# 保留:ASCII 字母数字 + 中文(基本区)。其余转连字符。
_KEEP = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")
_EXPLICIT = re.compile(r"\{#([0-9a-zA-Z\u4e00-\u9fff\-_]+)\}\s*$")


def slugify(text: str) -> str:
    """把标题文本转成稳定 slug。"""
    s = text.strip().lower()
    s = _KEEP.sub("-", s)
    s = s.strip("-")
    return s


def extract_explicit_anchor(heading: str) -> tuple[str, str | None]:
    """从标题文本里剥离 `{#anchor}` 显式锚点。

    返回 (清洗后的标题文本, 显式锚点或 None)。
    """
    m = _EXPLICIT.search(heading)
    if not m:
        return heading.strip(), None
    anchor = m.group(1)
    clean = heading[: m.start()].strip()
    return clean, anchor


def heading_anchor(heading: str) -> tuple[str, str]:
    """给标题算最终 (显示文本, anchor)。显式锚点优先,否则 slug。"""
    clean, explicit = extract_explicit_anchor(heading)
    return clean, (explicit or slugify(clean))
