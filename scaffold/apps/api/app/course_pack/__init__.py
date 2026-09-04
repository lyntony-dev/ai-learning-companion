"""课程包契约 (ADR-0002/0006)。引擎经此加载课程,零硬编码。"""

from app.course_pack.loader import CoursePackError, CoursePackLoader
from app.course_pack.schema import (
    ArtifactStatus,
    Attachment,
    Capstone,
    Course,
    CourseMaterials,
    CoursePack,
    CourseRubric,
    Courseware,
    Milestone,
    Question,
    QuestionDifficulty,
    QuestionSet,
    Rubric,
    RubricDimension,
    Taxonomy,
    Topic,
)

__all__ = [
    "CoursePackLoader",
    "CoursePackError",
    "CoursePack",
    "Course",
    "CourseMaterials",
    "Courseware",
    "Attachment",
    "Capstone",
    "Milestone",
    "Topic",
    "Taxonomy",
    "Question",
    "QuestionDifficulty",
    "QuestionSet",
    "Rubric",
    "CourseRubric",
    "RubricDimension",
    "ArtifactStatus",
]
