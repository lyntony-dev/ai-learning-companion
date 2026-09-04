from server import TOOL_SCHEMAS


def test_tool_schemas_include_required_tools() -> None:
    names = {tool.name for tool in TOOL_SCHEMAS}

    assert names == {"list_courses", "search_course_material", "get_course_chunk"}


def test_search_tool_requires_query() -> None:
    search_schema = next(tool for tool in TOOL_SCHEMAS if tool.name == "search_course_material")

    assert search_schema.input_schema["required"] == ["query"]
