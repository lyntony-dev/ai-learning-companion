import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.config import Settings

SQLITE_PREFIX = "sqlite:///"


class DatabaseConfigError(ValueError):
    """Raised when database configuration is unsupported."""


def resolve_sqlite_path(database_url: str) -> Path:
    """Resolve a sqlite:/// URL into an absolute or repository-relative path."""

    if not database_url.startswith(SQLITE_PREFIX):
        raise DatabaseConfigError("Only sqlite:/// DATABASE_URL values are supported in MVP-B.")

    raw_path = database_url.removeprefix(SQLITE_PREFIX)
    if not raw_path:
        raise DatabaseConfigError("SQLite database path cannot be empty.")

    return Path(raw_path)


def ensure_parent_dir(database_path: Path) -> None:
    """Create the parent directory for a SQLite database file when needed."""

    parent = database_path.parent
    if str(parent) not in {"", "."}:
        parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def connect(settings: Settings) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection with safe defaults for the MVP skeleton."""

    database_path = resolve_sqlite_path(settings.database_url)
    ensure_parent_dir(database_path)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
