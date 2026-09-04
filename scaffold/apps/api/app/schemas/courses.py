"""课程浏览 (学生视图) schema。

只读暴露 CoursePackLoader 已解析的课程/资料元数据,供前端浏览、进入课程、
并把引用来源(source_path)映射到可打开的资料文件。零课程硬编码。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MaterialRef(BaseModel):
    """一份可打开的资料。rel_path 相对 materials/,前端据此拼资料 URL。"""

    kind: str  # lecture_note | slide | code_example | attachment
    title: str
    rel_path: str


class CoursewareSection(BaseModel):
    """课件内的可寻址段(标题 → 锚点),供学生端目录跳转。"""

    anchor: str
    title: str


class CoursewareRef(BaseModel):
    """结构化课件 (CoursewareDoc v1)。rel_path 相对 courseware/。"""

    rel_path: str
    title: str
    sections: list[CoursewareSection] = Field(default_factory=list)


class CourseSummary(BaseModel):
    course_id: str
    name: str
    courseware: CoursewareRef | None = None
    materials: list[MaterialRef] = Field(default_factory=list)


class CoursePackSummary(BaseModel):
    course_pack_id: str
    name: str
    description: str = ""
    version: str = "v1"
    course_count: int = 0


class CoursePackListResponse(BaseModel):
    packs: list[CoursePackSummary] = Field(default_factory=list)


class CoursePackDetailResponse(BaseModel):
    course_pack_id: str
    name: str
    description: str = ""
    version: str = "v1"
    courses: list[CourseSummary] = Field(default_factory=list)
