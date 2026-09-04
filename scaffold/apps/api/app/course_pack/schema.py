"""课程包契约 schema (ADR-0002/0006 / DESIGN §6)。

引擎只依赖这些 Pydantic 对象,不直接读约定文件、不硬编码任何课程内容。
CoursePackLoader 负责把 data/course_packs/<id>/ 的约定文件解析为这些对象。
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ArtifactStatus(str, Enum):
    """候选产物审核状态(ADR-0006:AI 提取候选 → 讲师审核沉淀)。"""

    CANDIDATE = "candidate"
    APPROVED = "approved"


class CourseMaterials(BaseModel):
    """一门课的原始资料相对路径(相对 materials/)。"""

    lecture_note: str | None = None
    slides: list[str] = Field(default_factory=list)
    code_examples: str | None = None


class Attachment(BaseModel):
    """课件的原始附件(HTML PPT / PDF / 代码目录),相对 materials/。

    CoursewareDoc v1:结构化课件为主体,原始资料降为可下载/预览附件。
    """

    kind: str  # slides | pdf | code | other
    path: str
    title: str = ""


class Courseware(BaseModel):
    """结构化课件 (CoursewareDoc v1)。path 相对课程包 courseware/。"""

    path: str  # 相对 courseware/
    title: str = ""
    version: str = "v1"
    attachments: list[Attachment] = Field(default_factory=list)


class Course(BaseModel):
    course_id: str
    name: str
    materials: CourseMaterials = Field(default_factory=CourseMaterials)
    courseware: Courseware | None = None  # CoursewareDoc v1;有则学生端以此为主体


class Milestone(BaseModel):
    id: str
    name: str
    # 学生端引导(可选):本里程碑要交付什么、提示、一份范例提交
    deliverable: str = ""
    hint: str = ""
    sample_report: str = ""


class Capstone(BaseModel):
    name: str
    milestones: list[Milestone] = Field(default_factory=list)
    # 项目说明书(可选):目标、背景、最终交付
    overview: str = ""
    background: str = ""
    final_deliverable: str = ""


class Topic(BaseModel):
    """知识点(掌握度/个性化/出题最小单位)。"""

    id: str
    name: str
    course_id: str


class Taxonomy(BaseModel):
    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    topics: list[Topic] = Field(default_factory=list)


class QuestionDifficulty(str, Enum):
    """题目难度(自适应出题:弱→easy,一般→medium,强→hard)。"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(BaseModel):
    """预置题库中的一道题(讲师编写,加载器解析,入 QuestionBank)。"""

    id: str = ""  # 稳定 slug(可选);缺省时由加载/入库端按 prompt 哈希生成
    topic_id: str
    difficulty: QuestionDifficulty = QuestionDifficulty.MEDIUM
    prompt: str
    reference_answer: str = ""


class QuestionSet(BaseModel):
    """课程包题库(可选)。status 沿用候选/审核语义(ADR-0006)。"""

    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    questions: list[Question] = Field(default_factory=list)


class RubricDimension(BaseModel):
    key: str
    name: str
    weight: float = 0.0


class CourseRubric(BaseModel):
    """一门课的专项评分配置。

    dimensions:引用 default_dimensions 的 key 子集(缺省=全部默认维度)。
    extra_dimensions:课程特有的额外维度(不在默认集里)。
    """

    dimensions: list[str] = Field(default_factory=list)
    extra_dimensions: list[RubricDimension] = Field(default_factory=list)


class Rubric(BaseModel):
    status: ArtifactStatus = ArtifactStatus.CANDIDATE
    default_dimensions: list[RubricDimension] = Field(default_factory=list)
    by_course: dict[str, CourseRubric] = Field(default_factory=dict)


class CoursePack(BaseModel):
    """引擎消费的课程包统一对象。加载器产物,引擎唯一依赖面。"""

    course_pack_id: str
    name: str
    description: str = ""
    version: str = "v1"
    courses: list[Course] = Field(default_factory=list)
    capstone: Capstone | None = None
    taxonomy: Taxonomy = Field(default_factory=Taxonomy)
    rubric: Rubric = Field(default_factory=Rubric)
    questions: QuestionSet = Field(default_factory=QuestionSet)

    def topic_ids(self) -> list[str]:
        return [t.id for t in self.taxonomy.topics]

    def milestone_ids(self) -> list[str]:
        return [m.id for m in self.capstone.milestones] if self.capstone else []

    def get_course(self, course_id: str) -> Course | None:
        return next((c for c in self.courses if c.course_id == course_id), None)
