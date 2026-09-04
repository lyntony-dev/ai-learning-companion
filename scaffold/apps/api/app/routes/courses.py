"""课程浏览 (C 学生视图) 路由。

面向学生:
  - GET /api/courses                                   课程包列表(只读)
  - GET /api/courses/{course_pack_id}                  课程 + 资料清单(只读)
  - GET /api/courses/{course_pack_id}/materials/{rel}  打开原始资料文件

资料文件从课程包约定目录 materials/ 直读(HTML PPT / Markdown / 代码),
经 CoursePackLoader 校验声明与磁盘一致(ADR-0006)。零课程硬编码。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.course_pack import CoursePack, CoursePackLoader
from app.ingestion.pack_parsers import split_markdown_sections
from app.schemas.courses import (
    CoursePackDetailResponse,
    CoursePackListResponse,
    CoursePackSummary,
    CoursewareRef,
    CoursewareSection,
    CourseSummary,
    MaterialRef,
)

router = APIRouter(prefix="/api/courses", tags=["courses"])

# 可作为独立资料项打开的代码文件后缀(与摄取管线 pack_parsers.CODE_SUFFIXES 对齐)。
_CODE_SUFFIXES = {".py", ".ts", ".js", ".txt", ".json"}

# 资料 MIME:让 HTML PPT 直接在浏览器渲染,其余按文本预览。
_MEDIA_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".py": "text/plain; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".pdf": "application/pdf",
    ".json": "application/json; charset=utf-8",
}


def _load_pack(course_pack_id: str) -> CoursePack:
    try:
        return CoursePackLoader().load(course_pack_id)
    except Exception as exc:  # 课程包不存在/损坏
        raise HTTPException(
            status_code=404, detail=f"course_pack_not_found: {course_pack_id}"
        ) from exc


def _code_example_refs(course_pack_id: str, code_examples_rel: str) -> list[MaterialRef]:
    """把 code_examples 目录展开成其下真实代码文件的资料项。

    manifest 的 code_examples 指向一个目录,不能直接当文件打开;这里递归枚举
    可预览的代码文件(排除 node_modules),每个文件一条 MaterialRef。
    """
    materials_root = (CoursePackLoader().pack_dir(course_pack_id) / "materials").resolve()
    code_root = (materials_root / code_examples_rel).resolve()
    if not code_root.is_relative_to(materials_root) or not code_root.is_dir():
        return []
    refs: list[MaterialRef] = []
    for cp in sorted(code_root.rglob("*")):
        if not cp.is_file() or cp.suffix.lower() not in _CODE_SUFFIXES:
            continue
        if "node_modules" in cp.parts:
            continue
        rel = cp.relative_to(materials_root).as_posix()
        # 标题用相对 code_examples 目录的路径,便于区分同名文件。
        title = cp.relative_to(code_root).as_posix()
        refs.append(MaterialRef(kind="code_example", title=title, rel_path=rel))
    return refs


def _courseware_ref(course_pack_id: str, course) -> CoursewareRef | None:
    """把课程的结构化课件解析成前端可用的 CoursewareRef(含目录)。

    目录 (sections) 由课件正文标题实时切分得到,anchor 与摄取/引用同源,
    保证学生端点击目录/引用来源跳转不漂移(CoursewareDoc v1)。
    """
    cw = course.courseware
    if cw is None:
        return None
    courseware_root = (CoursePackLoader().pack_dir(course_pack_id) / "courseware").resolve()
    cw_path = (courseware_root / cw.path).resolve()
    sections: list[CoursewareSection] = []
    if cw_path.is_relative_to(courseware_root) and cw_path.is_file():
        raw = cw_path.read_text(encoding="utf-8")
        # 剥离 frontmatter(--- ... ---)后再切标题。
        body = raw
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]
        for heading, anchor, _ in split_markdown_sections(body):
            if heading:
                sections.append(CoursewareSection(anchor=anchor, title=heading))
    return CoursewareRef(rel_path=cw.path, title=cw.title or course.name, sections=sections)


def _attachment_refs(course_pack_id: str, course) -> list[MaterialRef]:
    """课件的原始附件(降级为可预览/下载项)。kind=attachment 便于前端区分主体。

    kind=code 的附件指向目录,不能直接当文件打开;展开成目录内真实代码文件,
    与无课件课程的 code_example 一致,避免前端预览目录报 content_fetch_failed。
    """
    cw = course.courseware
    if cw is None:
        return []
    refs: list[MaterialRef] = []
    for a in cw.attachments:
        materials_root = (CoursePackLoader().pack_dir(course_pack_id) / "materials").resolve()
        target = (materials_root / a.path).resolve()
        if a.kind == "code" and target.is_dir():
            refs.extend(_code_example_refs(course_pack_id, a.path))
        else:
            refs.append(MaterialRef(kind="attachment", title=a.title or a.path, rel_path=a.path))
    return refs


def _course_summaries(pack: CoursePack) -> list[CourseSummary]:
    summaries: list[CourseSummary] = []
    for course in pack.courses:
        courseware = _courseware_ref(pack.course_pack_id, course)
        if courseware is not None:
            # 有结构化课件:课件为主体,原始资料降为附件。
            summaries.append(
                CourseSummary(
                    course_id=course.course_id,
                    name=course.name,
                    courseware=courseware,
                    materials=_attachment_refs(pack.course_pack_id, course),
                )
            )
            continue
        # 无课件:回退到原始资料清单(向后兼容未转换的课程)。
        refs: list[MaterialRef] = []
        if course.materials.lecture_note:
            refs.append(
                MaterialRef(kind="lecture_note", title="讲义", rel_path=course.materials.lecture_note)
            )
        for i, slide in enumerate(course.materials.slides, start=1):
            refs.append(MaterialRef(kind="slide", title=f"课件 {i}", rel_path=slide))
        if course.materials.code_examples:
            refs.extend(_code_example_refs(pack.course_pack_id, course.materials.code_examples))
        summaries.append(
            CourseSummary(course_id=course.course_id, name=course.name, materials=refs)
        )
    return summaries


@router.get("", response_model=CoursePackListResponse)
def list_packs() -> CoursePackListResponse:
    loader = CoursePackLoader()
    packs: list[CoursePackSummary] = []
    for pack_id in loader.available_packs():
        try:
            pack = loader.load(pack_id)
        except Exception:  # 跳过损坏包,不影响其余
            continue
        packs.append(
            CoursePackSummary(
                course_pack_id=pack.course_pack_id,
                name=pack.name,
                description=pack.description,
                version=pack.version,
                course_count=len(pack.courses),
            )
        )
    return CoursePackListResponse(packs=packs)


@router.get("/{course_pack_id}", response_model=CoursePackDetailResponse)
def pack_detail(course_pack_id: str) -> CoursePackDetailResponse:
    pack = _load_pack(course_pack_id)
    return CoursePackDetailResponse(
        course_pack_id=pack.course_pack_id,
        name=pack.name,
        description=pack.description,
        version=pack.version,
        courses=_course_summaries(pack),
    )


@router.get("/{course_pack_id}/materials/{rel_path:path}")
def get_material(course_pack_id: str, rel_path: str) -> FileResponse:
    """打开一份资料文件。rel_path 相对课程包 materials/,做防越权解析。"""
    _load_pack(course_pack_id)  # 先校验课程包存在
    materials_root = (CoursePackLoader().pack_dir(course_pack_id) / "materials").resolve()
    target = (materials_root / rel_path).resolve()

    # 防路径穿越:目标必须落在 materials_root 内
    if not target.is_relative_to(materials_root):
        raise HTTPException(status_code=400, detail="invalid_material_path")
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"material_not_found: {rel_path}")

    media_type = _MEDIA_TYPES.get(target.suffix.lower(), "application/octet-stream")
    # inline(而非 attachment):让前端 iframe/embed 内联渲染 HTML PPT / PDF,
    # 而不是触发浏览器下载。
    return FileResponse(
        path=target,
        media_type=media_type,
        content_disposition_type="inline",
    )


@router.get("/{course_pack_id}/courseware/{rel_path:path}")
def get_courseware(course_pack_id: str, rel_path: str) -> FileResponse:
    """打开一份结构化课件正文(Markdown)。rel_path 相对课程包 courseware/。"""
    _load_pack(course_pack_id)  # 先校验课程包存在
    courseware_root = (CoursePackLoader().pack_dir(course_pack_id) / "courseware").resolve()
    target = (courseware_root / rel_path).resolve()

    # 防路径穿越:目标必须落在 courseware_root 内
    if not target.is_relative_to(courseware_root):
        raise HTTPException(status_code=400, detail="invalid_courseware_path")
    if not target.is_file():
        raise HTTPException(status_code=404, detail=f"courseware_not_found: {rel_path}")

    media_type = _MEDIA_TYPES.get(target.suffix.lower(), "text/markdown; charset=utf-8")
    return FileResponse(
        path=target,
        media_type=media_type,
        content_disposition_type="inline",
    )
