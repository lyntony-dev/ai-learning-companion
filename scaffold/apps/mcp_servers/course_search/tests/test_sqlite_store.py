import sqlite3
from pathlib import Path

from schemas.chunk import GetCourseChunkRequest, SearchCourseMaterialRequest
from storage import CourseSearchStore
from tools.get_course_chunk import get_course_chunk
from tools.list_courses import list_courses
from tools.search_course_material import search_course_material


def create_course_search_database(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        connection.executescript(
            """
            CREATE TABLE courses (
                course_id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                version TEXT NOT NULL DEFAULT 'v1',
                tags_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE course_chunks (
                chunk_id TEXT PRIMARY KEY,
                course_id TEXT NOT NULL,
                section TEXT NOT NULL,
                content_type TEXT NOT NULL,
                text_preview TEXT NOT NULL,
                source_path TEXT NOT NULL,
                slide_no INTEGER,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (course_id) REFERENCES courses(course_id)
            );
            """
        )
        connection.execute(
            """
            INSERT INTO courses(course_id, course_name, version, tags_json)
            VALUES ('demo_course', 'Demo Course：Agent 基础', 'v1', '["Agent", "RAG"]')
            """
        )
        connection.execute(
            """
            INSERT INTO course_chunks(
                chunk_id,
                course_id,
                section,
                content_type,
                text_preview,
                source_path,
                slide_no,
                metadata_json
            ) VALUES (
                'chunk_demo_001',
                'demo_course',
                'slide 01',
                'slide',
                'LangGraph State 用于在 Agent 图的多个节点之间传递上下文。',
                'demo_course/slides/slide_01.md',
                1,
                '{"course_version": "v1"}'
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_list_courses_reads_sqlite_courses(tmp_path: Path) -> None:
    database_path = tmp_path / "course_search.sqlite"
    create_course_search_database(database_path)
    store = CourseSearchStore(f"sqlite:///{database_path}")

    response = list_courses(store)

    assert len(response.courses) == 1
    assert response.courses[0].course_id == "demo_course"
    assert response.courses[0].tags == ["Agent", "RAG"]


def test_search_course_material_reads_sqlite_chunks(tmp_path: Path) -> None:
    database_path = tmp_path / "course_search.sqlite"
    create_course_search_database(database_path)
    store = CourseSearchStore(f"sqlite:///{database_path}")

    response = search_course_material(
        SearchCourseMaterialRequest(
            query="LangGraph State",
            course_ids=["demo_course"],
            content_types=["slide"],
            top_k=5,
        ),
        store,
    )

    assert response.query_used == "LangGraph State"
    assert len(response.results) == 1
    assert response.results[0].chunk_id == "chunk_demo_001"
    assert response.results[0].course_name == "Demo Course：Agent 基础"
    assert response.results[0].score > 0


def test_get_course_chunk_reads_sqlite_chunk(tmp_path: Path) -> None:
    database_path = tmp_path / "course_search.sqlite"
    create_course_search_database(database_path)
    store = CourseSearchStore(f"sqlite:///{database_path}")

    response = get_course_chunk(GetCourseChunkRequest(chunk_id="chunk_demo_001"), store)

    assert response.chunk is not None
    assert response.chunk.chunk_id == "chunk_demo_001"
    assert response.chunk.slide_no == 1
    assert response.error is None
