-- 002 全保真历史:给 messages 增加全文 content 与关联 trace_id。
-- content_summary 保留(会话标题/列表预览);content 存回答/提问全文;
-- trace_id 关联本轮 traces,让历史 assistant 消息可恢复 Agent Trace。
-- 两列可空以兼容 001 已有旧行。

ALTER TABLE messages ADD COLUMN content TEXT;
ALTER TABLE messages ADD COLUMN trace_id TEXT;

CREATE INDEX IF NOT EXISTS idx_messages_trace_id ON messages(trace_id);
