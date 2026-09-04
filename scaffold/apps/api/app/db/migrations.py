from pathlib import Path

import sqlite3

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def list_migration_files(migrations_dir: Path = MIGRATIONS_DIR) -> list[Path]:
    """Return migration files sorted by version prefix."""

    return sorted(migrations_dir.glob("*.sql"))


def ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def applied_versions(connection: sqlite3.Connection) -> set[str]:
    ensure_migration_table(connection)
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {str(row["version"]) for row in rows}


def apply_migrations(connection: sqlite3.Connection) -> list[str]:
    """Apply pending SQL migrations and return applied version names."""

    ensure_migration_table(connection)
    applied = applied_versions(connection)
    newly_applied: list[str] = []

    for migration_file in list_migration_files():
        version = migration_file.stem
        if version in applied:
            continue

        connection.executescript(migration_file.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
        newly_applied.append(version)

    return newly_applied
