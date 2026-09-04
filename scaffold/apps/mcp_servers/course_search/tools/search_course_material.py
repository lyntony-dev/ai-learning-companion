import time

from schemas.chunk import CourseChunk, SearchCourseMaterialRequest, SearchCourseMaterialResponse
from storage import CourseSearchStore

MOCK_CHUNKS = [
    CourseChunk(
        chunk_id="mock_chunk_001",
        course_id="ppt2_langgraph",
        course_name="PPT2：LangGraph 与多 Agent",
        section="StateGraph",
        slide_no=6,
        content_type="slide",
        text="Mock chunk text for PR 1. LangGraph State carries intermediate results across graph nodes.",
        score=0.9,
        source_path="data/course_materials/ppt2_langgraph/slides/slide_06.html",
    ),
    CourseChunk(
        chunk_id="mock_chunk_002",
        course_id="ppt3_mcp",
        course_name="PPT3：MCP 与 Agent 工具生态",
        section="MCP Server",
        slide_no=8,
        content_type="slide",
        text="Mock chunk text for PR 1. MCP Server exposes tools and resources to agents.",
        score=0.82,
        source_path="data/course_materials/ppt3_mcp/slides/slide_08.html",
    ),
]


def search_course_material(
    request: SearchCourseMaterialRequest,
    store: CourseSearchStore | None = None,
) -> SearchCourseMaterialResponse:
    started_at = time.perf_counter()
    course_store = store or CourseSearchStore()
    if course_store.is_available():
        results = course_store.search_chunks(
            request.query,
            request.course_ids,
            request.content_types,
            request.top_k,
        )
    else:
        results = _search_mock_chunks(request)

    return SearchCourseMaterialResponse(
        results=results,
        query_used=request.query,
        latency_ms=max(1, round((time.perf_counter() - started_at) * 1000)),
    )


def _search_mock_chunks(request: SearchCourseMaterialRequest) -> list[CourseChunk]:
    filtered = MOCK_CHUNKS
    if request.course_ids:
        filtered = [chunk for chunk in filtered if chunk.course_id in request.course_ids]
    if request.content_types:
        filtered = [chunk for chunk in filtered if chunk.content_type in request.content_types]
    return filtered[: request.top_k]
