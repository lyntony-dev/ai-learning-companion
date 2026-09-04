import sqlite3

from app.db.migrations import apply_migrations
from app.models.trace import TraceEventRecord, TraceRecord
from app.repositories.trace_repository import TraceRepository


def test_trace_repository_writes_and_reads_events() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    apply_migrations(connection)
    repository = TraceRepository(connection)

    repository.create_trace(
        TraceRecord(
            trace_id="trace_001",
            request_id="request_001",
            user_id="demo_user",
            status="success",
            total_latency_ms=42,
            token_usage={"prompt_tokens": 10, "completion_tokens": 20},
        )
    )
    repository.append_event(
        TraceEventRecord(
            event_id="event_001",
            trace_id="trace_001",
            node_name="Retrieve",
            status="success",
            latency_ms=12,
            input_summary="top_k=5",
            output_summary="1 chunk",
            metadata={"evidence_level": "strong"},
        )
    )

    events = repository.list_events("trace_001")

    assert len(events) == 1
    assert events[0].node_name == "Retrieve"
    assert events[0].metadata == {"evidence_level": "strong"}
