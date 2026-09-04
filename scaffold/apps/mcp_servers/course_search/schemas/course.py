from pydantic import BaseModel, Field


class Course(BaseModel):
    course_id: str
    course_name: str
    version: str = "v1"
    tags: list[str] = Field(default_factory=list)


class ListCoursesResponse(BaseModel):
    courses: list[Course]
