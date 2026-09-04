from pydantic import BaseModel, Field


class CourseManifest(BaseModel):
    course_id: str
    course_name: str
    version: str = "v1"
    tags: list[str] = Field(default_factory=list)


class MaterialDocument(BaseModel):
    course_id: str
    course_name: str
    version: str
    tags: list[str]
    source_path: str
    section: str
    content_type: str
    text: str
    slide_no: int | None = None


class CourseChunkDraft(BaseModel):
    chunk_id: str
    course_id: str
    course_name: str
    section: str
    content_type: str
    text_preview: str
    source_path: str
    slide_no: int | None = None
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class ValidationIssue(BaseModel):
    level: str
    path: str
    message: str


class ValidationReport(BaseModel):
    valid: bool
    course_count: int
    document_count: int
    chunk_count: int
    issues: list[ValidationIssue] = Field(default_factory=list)


class ImportReport(BaseModel):
    status: str
    rebuild: bool
    courses_imported: int
    chunks_imported: int
    issues: list[ValidationIssue] = Field(default_factory=list)
