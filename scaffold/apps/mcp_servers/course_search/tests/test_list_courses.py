from tools.list_courses import list_courses


def test_list_courses_returns_mock_courses() -> None:
    response = list_courses()

    assert len(response.courses) >= 1
    assert response.courses[0].course_id == "ppt2_langgraph"
