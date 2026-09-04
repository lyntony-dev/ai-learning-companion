from pydantic import BaseModel, Field


class ConversationRecord(BaseModel):
    conversation_id: str
    user_id: str
    title: str


class MessageRecord(BaseModel):
    message_id: str
    conversation_id: str
    role: str
    content_summary: str
    # 全文(002 起):恢复历史时用它,回退 content_summary 兼容旧行。
    content: str | None = None
    # 关联本轮 trace(仅 assistant 消息),用于历史 Agent Trace 恢复。
    trace_id: str | None = None
    citations: list[dict[str, str | int | None]] = Field(default_factory=list)
