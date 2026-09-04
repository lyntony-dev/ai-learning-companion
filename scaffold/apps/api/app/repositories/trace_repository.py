import json
import sqlite3

from app.models.trace import TraceEventRecord, TraceRecord


class TraceRepository:
    """SQLite repository for trace summaries.

    Stores only summaries and metadata by default. Full prompts, full user inputs,
    full model outputs, secrets, and full retrieved chunk text must not be written here.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def create_trace(self, trace: TraceRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO traces(
                trace_id,
                conversation_id,
                request_id,
                user_id,
                status,
                total_latency_ms,
                token_usage_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace.trace_id,
                trace.conversation_id,
                trace.request_id,
                trace.user_id,
                trace.status,
                trace.total_latency_ms,
                json.dumps(trace.token_usage, ensure_ascii=False),
            ),
        )

    def append_event(self, event: TraceEventRecord) -> None:
        self._connection.execute(
            """
            INSERT INTO trace_events(
                event_id,
                trace_id,
                node_name,
                status,
                latency_ms,
                input_summary,
                output_summary,
                metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.trace_id,
                event.node_name,
                event.status,
                event.latency_ms,
                event.input_summary,
                event.output_summary,
                json.dumps(event.metadata, ensure_ascii=False),
            ),
        )

    def list_events(self, trace_id: str) -> list[TraceEventRecord]:
        rows = self._connection.execute(
            """
            SELECT event_id, trace_id, node_name, status, latency_ms,
                   input_summary, output_summary, metadata_json
            FROM trace_events
            WHERE trace_id = ?
            ORDER BY created_at ASC
            """,
            (trace_id,),
        ).fetchall()

        return [
            TraceEventRecord(
                event_id=str(row["event_id"]),
                trace_id=str(row["trace_id"]),
                node_name=str(row["node_name"]),
                status=str(row["status"]),
                latency_ms=int(row["latency_ms"]),
                input_summary=str(row["input_summary"]),
                output_summary=str(row["output_summary"]),
                metadata=json.loads(str(row["metadata_json"])),
            )
            for row in rows
        ]
