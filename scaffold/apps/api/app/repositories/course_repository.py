import json
import sqlite3

from app.ingestion.models import CourseChunkDraft, CourseManifest


class CourseRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def clear_all(self) -> None:
        self._connection.execute("DELETE FROM course_chunks")
        self._connection.execute("DELETE FROM courses")

    def upsert_course(self, manifest: CourseManifest) -> None:
        self._connection.execute(
            """
            INSERT INTO courses(course_id, course_name, version, tags_json, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT(course_id) DO UPDATE SET
                course_name = excluded.course_name,
                version = excluded.version,
                tags_json = excluded.tags_json,
                updated_at = datetime('now')
            """,
            (
                manifest.course_id,
                manifest.course_name,
                manifest.version,
                json.dumps(manifest.tags, ensure_ascii=False),
            ),
        )

    def upsert_chunk(self, chunk: CourseChunkDraft) -> None:
        self._connection.execute(
            """
            INSERT INTO course_chunks(
                chunk_id,
                course_id,
                section,
                content_type,
                text_preview,
                source_path,
                slide_no,
                metadata_json,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(chunk_id) DO UPDATE SET
                course_id = excluded.course_id,
                section = excluded.section,
                content_type = excluded.content_type,
                text_preview = excluded.text_preview,
                source_path = excluded.source_path,
                slide_no = excluded.slide_no,
                metadata_json = excluded.metadata_json,
                updated_at = datetime('now')
            """,
            (
                chunk.chunk_id,
                chunk.course_id,
                chunk.section,
                chunk.content_type,
                chunk.text_preview,
                chunk.source_path,
                chunk.slide_no,
                json.dumps(chunk.metadata, ensure_ascii=False),
            ),
        )

    def count_courses(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS count FROM courses").fetchone()
        return int(row["count"])

    def count_chunks(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS count FROM course_chunks").fetchone()
        return int(row["count"])
