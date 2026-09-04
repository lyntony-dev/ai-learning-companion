from pydantic import BaseModel, Field


class TraceRecord(BaseModel):
    trace_id: str
    conversation_id: str | None = None
    request_id: str
    user_id: str
    status: str
    total_latency_ms: int = 0
    token_usage: dict[str, int] = Field(default_factory=dict)


class TraceEventRecord(BaseModel):
    event_id: str
    trace_id: str
    node_name: str
    status: str
    latency_ms: int = 0
    input_summary: str = ""
    output_summary: str = ""
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
