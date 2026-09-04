import sqlite3
from pathlib import Path

from app.db.migrations import apply_migrations
from app.ingestion.service import import_materials
from app.repositories.course_repository import CourseRepository


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "course_materials"


def test_import_materials_writes_course_and_chunk_metadata() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    apply_migrations(connection)
    repository = CourseRepository(connection)

    report = import_materials(FIXTURES_DIR, repository, rebuild=True)

    assert report.status == "ok"
    assert report.rebuild is True
    assert report.courses_imported == 1
    assert report.chunks_imported == 1
    assert repository.count_courses() == 1
    assert repository.count_chunks() == 1

    course = connection.execute("SELECT course_id, course_name FROM courses").fetchone()
    chunk = connection.execute("SELECT course_id, content_type, slide_no FROM course_chunks").fetchone()

    assert course["course_id"] == "demo_course"
    assert course["course_name"] == "Demo Course：Agent 基础"
    assert chunk["course_id"] == "demo_course"
    assert chunk["content_type"] == "slide"
    assert chunk["slide_no"] == 1
