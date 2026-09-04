import json
import sqlite3

from app.models.conversation import ConversationRecord, MessageRecord


class ConversationRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create_conversation(self, conversation: ConversationRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO conversations(conversation_id, user_id, title, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(conversation_id) DO UPDATE SET
                title = excluded.title,
                updated_at = datetime('now')
            """,
            (conversation.conversation_id, conversation.user_id, conversation.title),
        )

    def append_message(self, message: MessageRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO messages(
                message_id, conversation_id, role, content_summary,
                content, trace_id, citations_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message.message_id,
                message.conversation_id,
                message.role,
                message.content_summary,
                message.content,
                message.trace_id,
                json.dumps(message.citations, ensure_ascii=False),
            ),
        )
        self._connection.execute(
            """
            UPDATE conversations
            SET updated_at = datetime('now')
            WHERE conversation_id = ?
            """,
            (message.conversation_id,),
        )

    def list_conversations(self, user_id: str) -> list[ConversationRecord]:
        rows = self._connection.execute(
            """
            SELECT conversation_id, user_id, title
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [
            ConversationRecord(
                conversation_id=str(row["conversation_id"]),
                user_id=str(row["user_id"]),
                title=str(row["title"]),
            )
            for row in rows
        ]

    def list_messages(self, conversation_id: str) -> list[MessageRecord]:
        rows = self._connection.execute(
            """
            SELECT message_id, conversation_id, role, content_summary,
                   content, trace_id, citations_json
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()
        return [
            MessageRecord(
                message_id=str(row["message_id"]),
                conversation_id=str(row["conversation_id"]),
                role=str(row["role"]),
                content_summary=str(row["content_summary"]),
                content=str(row["content"]) if row["content"] is not None else None,
                trace_id=str(row["trace_id"]) if row["trace_id"] is not None else None,
                citations=json.loads(row["citations_json"]) if row["citations_json"] else [],
            )
            for row in rows
        ]

    def delete_conversation(self, conversation_id: str) -> None:
        # SQLite 未开启级联,需按外键依赖顺序手动清理:
        # trace_events → traces → messages → conversation。
        self._connection.execute(
            """
            DELETE FROM trace_events
            WHERE trace_id IN (
                SELECT trace_id FROM traces WHERE conversation_id = ?
            )
            """,
            (conversation_id,),
        )
        self._connection.execute(
            "DELETE FROM traces WHERE conversation_id = ?",
            (conversation_id,),
        )
        self._connection.execute(
            "DELETE FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        self._connection.execute(
            "DELETE FROM conversations WHERE conversation_id = ?",
            (conversation_id,),
        )
