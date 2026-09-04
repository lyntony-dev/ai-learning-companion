import json
import os
import sqlite3
from pathlib import Path

from schemas.chunk import CourseChunk
from schemas.course import Course

SQLITE_PREFIX = "sqlite:///"


class CourseSearchStore:
    """Read-only SQLite access for course metadata imported by the API ingestion CLI."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "sqlite:///data/app.sqlite")

    def is_available(self) -> bool:
        database_path = self._database_path()
        if database_path is None or not database_path.exists():
            return False

        try:
            with self._connect() as connection:
                return self._has_required_tables(connection)
        except sqlite3.Error:
            return False

    def list_courses(self) -> list[Course]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT course_id, course_name, version, tags_json
                FROM courses
                ORDER BY course_id ASC
                """
            ).fetchall()

        return [
            Course(
                course_id=str(row["course_id"]),
                course_name=str(row["course_name"]),
                version=str(row["version"]),
                tags=self._loads_list(str(row["tags_json"])),
            )
            for row in rows
        ]

    def search_chunks(
        self,
        query: str,
        course_ids: list[str],
        content_types: list[str],
        top_k: int,
    ) -> list[CourseChunk]:
        filters: list[str] = []
        params: list[str] = []

        if course_ids:
            filters.append(f"chunk.course_id IN ({','.join('?' for _ in course_ids)})")
            params.extend(course_ids)
        if content_types:
            filters.append(f"chunk.content_type IN ({','.join('?' for _ in content_types)})")
            params.extend(content_types)

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    chunk.chunk_id,
                    chunk.course_id,
                    course.course_name,
                    chunk.section,
                    chunk.content_type,
                    chunk.text_preview,
                    chunk.source_path,
                    chunk.slide_no
                FROM course_chunks AS chunk
                JOIN courses AS course ON course.course_id = chunk.course_id
                {where_clause}
                ORDER BY chunk.updated_at DESC, chunk.chunk_id ASC
                """,
                params,
            ).fetchall()

        chunks = [self._row_to_chunk(row, score=self._score_row(query, row)) for row in rows]
        ranked = sorted(chunks, key=lambda chunk: chunk.score, reverse=True)
        return ranked[:top_k]

    def get_chunk(self, chunk_id: str) -> CourseChunk | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    chunk.chunk_id,
                    chunk.course_id,
                    course.course_name,
                    chunk.section,
                    chunk.content_type,
                    chunk.text_preview,
                    chunk.source_path,
                    chunk.slide_no
                FROM course_chunks AS chunk
                JOIN courses AS course ON course.course_id = chunk.course_id
                WHERE chunk.chunk_id = ?
                """,
                (chunk_id,),
            ).fetchone()

        if row is None:
            return None
        return self._row_to_chunk(row, score=1.0)

    def _database_path(self) -> Path | None:
        if not self.database_url.startswith(SQLITE_PREFIX):
            return None
        raw_path = self.database_url.removeprefix(SQLITE_PREFIX)
        if not raw_path:
            return None
        return Path(raw_path)

    def _connect(self) -> sqlite3.Connection:
        database_path = self._database_path()
        if database_path is None:
            raise ValueError("Only sqlite:/// DATABASE_URL values are supported.")
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _has_required_tables(self, connection: sqlite3.Connection) -> bool:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name IN ('courses', 'course_chunks')
            """
        ).fetchall()
        return {str(row["name"]) for row in rows} == {"courses", "course_chunks"}

    def _row_to_chunk(self, row: sqlite3.Row, score: float) -> CourseChunk:
        return CourseChunk(
            chunk_id=str(row["chunk_id"]),
            course_id=str(row["course_id"]),
            course_name=str(row["course_name"]),
            section=str(row["section"]),
            content_type=str(row["content_type"]),
            text=str(row["text_preview"]),
            score=round(score, 4),
            source_path=str(row["source_path"]),
            slide_no=row["slide_no"],
        )

    def _score_row(self, query: str, row: sqlite3.Row) -> float:
        tokens = [token.lower() for token in query.replace("？", " ").replace("?", " ").split()]
        if not tokens:
            return 0.5

        haystack = " ".join(
            [
                str(row["course_name"]),
                str(row["section"]),
                str(row["content_type"]),
                str(row["text_preview"]),
            ]
        ).lower()
        matched = sum(1 for token in tokens if token in haystack)
        return matched / len(tokens)

    def _loads_list(self, value: str) -> list[str]:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item) for item in parsed]
