from pydantic import BaseModel, Field


class CourseChunk(BaseModel):
    chunk_id: str
    course_id: str
    course_name: str
    section: str
    content_type: str
    text: str
    score: float
    source_path: str
    slide_no: int | None = None


class SearchCourseMaterialRequest(BaseModel):
    query: str
    course_ids: list[str] = Field(default_factory=list)
    content_types: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchCourseMaterialResponse(BaseModel):
    results: list[CourseChunk]
    query_used: str
    latency_ms: int


class GetCourseChunkRequest(BaseModel):
    chunk_id: str


class GetCourseChunkResponse(BaseModel):
    chunk: CourseChunk | None
    error: str | None = None
