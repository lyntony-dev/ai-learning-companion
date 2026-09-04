from schemas.chunk import GetCourseChunkRequest, GetCourseChunkResponse
from storage import CourseSearchStore
from tools.search_course_material import MOCK_CHUNKS


def get_course_chunk(
    request: GetCourseChunkRequest,
    store: CourseSearchStore | None = None,
) -> GetCourseChunkResponse:
    course_store = store or CourseSearchStore()
    if course_store.is_available():
        chunk = course_store.get_chunk(request.chunk_id)
        if chunk is not None:
            return GetCourseChunkResponse(chunk=chunk)
        return GetCourseChunkResponse(chunk=None, error="chunk_not_found")

    for chunk in MOCK_CHUNKS:
        if chunk.chunk_id == request.chunk_id:
            return GetCourseChunkResponse(chunk=chunk)
    return GetCourseChunkResponse(chunk=None, error="chunk_not_found")
