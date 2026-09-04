import sqlite3

from app.db.migrations import apply_migrations


def test_apply_migrations_creates_core_tables() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row

    applied = apply_migrations(connection)

    assert applied == ["001_initial_schema", "002_message_full_fidelity"]
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    table_names = {str(row["name"]) for row in rows}
    assert {
        "schema_migrations",
        "courses",
        "course_chunks",
        "conversations",
        "messages",
        "traces",
        "trace_events",
        "eval_cases",
    }.issubset(table_names)

    # 002 全保真:messages 应含 content 与 trace_id 列。
    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(messages)").fetchall()
    }
    assert {"content", "trace_id"}.issubset(columns)
