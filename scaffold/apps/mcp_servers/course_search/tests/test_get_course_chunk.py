from schemas.chunk import GetCourseChunkRequest
from tools.get_course_chunk import get_course_chunk


def test_get_course_chunk_returns_chunk() -> None:
    response = get_course_chunk(GetCourseChunkRequest(chunk_id="mock_chunk_001"))

    assert response.chunk is not None
    assert response.chunk.chunk_id == "mock_chunk_001"
    assert response.error is None


def test_get_course_chunk_returns_structured_error() -> None:
    response = get_course_chunk(GetCourseChunkRequest(chunk_id="missing"))

    assert response.chunk is None
    assert response.error == "chunk_not_found"
