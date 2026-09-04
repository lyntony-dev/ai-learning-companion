from schemas.chunk import SearchCourseMaterialRequest
from tools.search_course_material import search_course_material


def test_search_course_material_returns_filtered_mock_chunks() -> None:
    response = search_course_material(
        SearchCourseMaterialRequest(
            query="LangGraph State 是什么？",
            course_ids=["ppt2_langgraph"],
            content_types=["slide"],
            top_k=5,
        )
    )

    assert response.query_used == "LangGraph State 是什么？"
    assert len(response.results) == 1
    assert response.results[0].chunk_id == "mock_chunk_001"
