"""共享 DTO(response/schema 层复用)。

编排层已迁移到 app.engine(真 LangGraph StateGraph,ADR-0001);
此处仅保留 API 响应层仍复用的引用/轨迹事件模型。
"""

from pydantic import BaseModel, Field


class Citation(BaseModel):
    citation_id: int
    chunk_id: str
    course_id: str
    course_name: str
    section: str
    source_path: str
    slide_no: int | None = None
    anchor_type: str = "none"
    anchor_value: str = ""


class AgentTraceEvent(BaseModel):
    node_name: str
    status: str
    input_summary: str = ""
    output_summary: str = ""
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
