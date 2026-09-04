"""课程包摄取解析器 (ADR-0006 / DESIGN §6)。

从 CoursePack 对象出发,解析原始资料(HTML PPT / MD / 代码 / PDF)为 MaterialDoc。
与脚手架旧 ingestion/parsers.py(course.json + 旧 RAG 库)独立,课程包感知。

MVP 文本层:
  - HTML PPT: 按 <section data-mira-slide> 分页去壳取正文,保 slide_no
  - Markdown / txt / 代码: 直取
  - PDF: pypdf 逐页抽文本(V2 再做 VLM 图片解析)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

from app.course_pack.schema import Course, CoursePack
from app.course_pack.slug import heading_anchor

# content_type 枚举(CONTEXT);MVP 落地 slide/lecture_note/code_example/courseware
CONTENT_LECTURE_NOTE = "lecture_note"
CONTENT_SLIDE = "slide"
CONTENT_CODE = "code_example"
CONTENT_COURSEWARE = "courseware"

CODE_SUFFIXES = {".py", ".ts", ".js", ".txt", ".json"}

# anchor_type:引用可定位单元的类型 (CoursewareDoc v1)
ANCHOR_HEADING = "heading"  # 课件标题段,anchor_value=slug
ANCHOR_SLIDE = "slide"  # HTML PPT 页,anchor_value=页码
ANCHOR_PAGE = "page"  # PDF 页,anchor_value=页码
ANCHOR_NONE = "none"


@dataclass
class MaterialDoc:
    """一个可分块的资料单元(某课/某内容类型/某页/某标题段)。"""

    course_pack_id: str
    course_id: str
    content_type: str
    source_path: str  # 相对 materials/ 或 courseware/
    text: str
    slide_no: int | None = None
    section: str = ""
    anchor_type: str = ANCHOR_NONE
    anchor_value: str = ""
    metadata: dict = field(default_factory=dict)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_html_slides(html: str) -> list[tuple[int, str]]:
    """HTML PPT 去壳,按 section 分页。返回 [(slide_no, text)]。"""
    soup = BeautifulSoup(html, "html.parser")
    # 丢弃样式/脚本
    for tag in soup(["style", "script"]):
        tag.decompose()

    sections = soup.find_all("section", attrs={"data-mira-slide": True})
    if not sections:
        # 回退:整篇当一页
        text = soup.get_text(separator="\n", strip=True)
        return [(1, text)] if text else []

    pages: list[tuple[int, str]] = []
    for idx, section in enumerate(sections, start=1):
        text = section.get_text(separator="\n", strip=True)
        if text:
            pages.append((idx, text))
    return pages


def parse_pdf(path: Path) -> list[tuple[int, str]]:
    """PDF 逐页抽文本。返回 [(page_no, text)]。"""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []
    for idx, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append((idx, text))
    return pages


def split_markdown_sections(text: str) -> list[tuple[str, str, str]]:
    """按 Markdown 二级及以下标题(## ~ ######)把课件正文切成可寻址段。

    返回 [(标题显示文本, anchor slug, 段落正文)]。正文含标题行下、直到下一个
    同级或更高级标题之间的内容。frontmatter(--- ... ---)在调用前已剥离。
    每个二级标题即一个可寻址单元(CoursewareDoc v1)。
    """
    lines = text.splitlines()
    sections: list[tuple[str, str, str]] = []
    cur_heading: str | None = None
    cur_anchor = ""
    buf: list[str] = []
    in_fence = False

    def flush() -> None:
        if cur_heading is not None:
            sections.append((cur_heading, cur_anchor, "\n".join(buf).strip()))

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            buf.append(line)
            continue
        if not in_fence and stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if 2 <= level <= 6 and stripped[level : level + 1] == " ":
                flush()
                raw = stripped[level:].strip()
                clean, anchor = heading_anchor(raw)
                cur_heading = clean
                cur_anchor = anchor
                buf = []
                continue
        buf.append(line)
    flush()
    return sections


def parse_courseware(
    pack: CoursePack, course: Course, courseware_root: Path
) -> list[MaterialDoc]:
    """解析结构化课件为按标题分段的 MaterialDoc(每段一个 heading anchor)。"""
    cw = course.courseware
    if cw is None:
        return []
    p = courseware_root / cw.path
    if not p.exists():
        return []
    raw = _read_text(p)
    # 剥离 frontmatter(--- ... ---),只切正文。
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]

    docs: list[MaterialDoc] = []
    for heading, anchor, section_text in split_markdown_sections(body):
        content = section_text.strip()
        if not content:
            continue
        # 段正文前置标题,保留语义上下文供检索。
        full = f"{heading}\n\n{content}" if heading else content
        docs.append(
            MaterialDoc(
                course_pack_id=pack.course_pack_id,
                course_id=course.course_id,
                content_type=CONTENT_COURSEWARE,
                source_path=cw.path,
                text=full,
                section=heading,
                anchor_type=ANCHOR_HEADING,
                anchor_value=anchor,
            )
        )
    return docs


def parse_course_materials(
    pack: CoursePack, course: Course, materials_root: Path
) -> list[MaterialDoc]:
    """解析一门课声明的全部资料为 MaterialDoc 列表。

    有结构化课件的课以课件为检索主体(附件不入索引,仅供预览/下载);
    无课件的课回退到原始资料(讲义/幻灯/代码),保证不回归。
    """
    if course.courseware is not None:
        courseware_root = materials_root.parent / "courseware"
        cw_docs = parse_courseware(pack, course, courseware_root)
        if cw_docs:
            return cw_docs

    docs: list[MaterialDoc] = []
    mats = course.materials

    # 讲义
    if mats.lecture_note:
        p = materials_root / mats.lecture_note
        if p.exists():
            text = _read_text(p).strip()
            if text:
                docs.append(
                    MaterialDoc(
                        course_pack_id=pack.course_pack_id,
                        course_id=course.course_id,
                        content_type=CONTENT_LECTURE_NOTE,
                        source_path=mats.lecture_note,
                        text=text,
                        section=p.stem,
                    )
                )

    # 幻灯片(HTML 去壳按页 / PDF 逐页)
    for rel in mats.slides:
        p = materials_root / rel
        if not p.exists():
            continue
        suffix = p.suffix.lower()
        if suffix in {".html", ".htm"}:
            pages = parse_html_slides(_read_text(p))
        elif suffix == ".pdf":
            pages = parse_pdf(p)
        else:
            continue
        for slide_no, text in pages:
            docs.append(
                MaterialDoc(
                    course_pack_id=pack.course_pack_id,
                    course_id=course.course_id,
                    content_type=CONTENT_SLIDE,
                    source_path=rel,
                    text=text,
                    slide_no=slide_no,
                    section=f"{p.stem} p{slide_no}",
                    anchor_type=ANCHOR_PAGE if suffix == ".pdf" else ANCHOR_SLIDE,
                    anchor_value=str(slide_no),
                )
            )

    # 代码示例(目录递归,排除 node_modules)
    if mats.code_examples:
        code_root = materials_root / mats.code_examples
        if code_root.exists() and code_root.is_dir():
            for cp in sorted(code_root.rglob("*")):
                if not cp.is_file() or cp.suffix.lower() not in CODE_SUFFIXES:
                    continue
                if "node_modules" in cp.parts:
                    continue
                text = _read_text(cp).strip()
                if not text:
                    continue
                docs.append(
                    MaterialDoc(
                        course_pack_id=pack.course_pack_id,
                        course_id=course.course_id,
                        content_type=CONTENT_CODE,
                        source_path=cp.relative_to(materials_root).as_posix(),
                        text=text,
                        section=cp.stem,
                    )
                )

    return docs


def parse_pack(pack: CoursePack, materials_root: Path) -> list[MaterialDoc]:
    """解析整个课程包的全部课程资料。"""
    docs: list[MaterialDoc] = []
    for course in pack.courses:
        docs.extend(parse_course_materials(pack, course, materials_root))
    return docs
