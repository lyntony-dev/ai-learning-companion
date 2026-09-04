from pydantic import BaseModel, Field

from app.agent.models import AgentTraceEvent, Citation


class ChatRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    user_id: str = "demo_user"
    course_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    conversation_id: str
    trace_id: str
    answer: str
    status: str
    citations: list[Citation] = Field(default_factory=list)
    trace: list[AgentTraceEvent] = Field(default_factory=list)


class ConversationSummary(BaseModel):
    conversation_id: str
    user_id: str
    title: str


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]


class MessageSummary(BaseModel):
    message_id: str
    conversation_id: str
    role: str
    content_summary: str
    content: str | None = None
    trace_id: str | None = None
    citations: list[dict[str, str | int | None]] = Field(default_factory=list)


class MessageListResponse(BaseModel):
    messages: list[MessageSummary]


class TraceEventSummary(BaseModel):
    event_id: str
    trace_id: str
    node_name: str
    status: str
    latency_ms: int = 0
    input_summary: str = ""
    output_summary: str = ""
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class TraceResponse(BaseModel):
    trace_id: str
    events: list[TraceEventSummary]
