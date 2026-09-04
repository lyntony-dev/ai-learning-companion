from schemas.tool import ToolSchema
from tools.get_course_chunk import get_course_chunk
from tools.list_courses import list_courses
from tools.search_course_material import search_course_material

TOOL_SCHEMAS = [
    ToolSchema(
        name="list_courses",
        description="List courses visible to the current mock user.",
        input_schema={"type": "object", "properties": {}},
        output_schema={"type": "object", "properties": {"courses": {"type": "array"}}},
    ),
    ToolSchema(
        name="search_course_material",
        description="Search course materials by natural language query and filters.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "course_ids": {"type": "array", "items": {"type": "string"}},
                "content_types": {"type": "array", "items": {"type": "string"}},
                "top_k": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
        output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
    ),
    ToolSchema(
        name="get_course_chunk",
        description="Get a course chunk by chunk_id.",
        input_schema={
            "type": "object",
            "properties": {"chunk_id": {"type": "string"}},
            "required": ["chunk_id"],
        },
        output_schema={"type": "object", "properties": {"chunk": {"type": ["object", "null"]}}},
    ),
]

__all__ = [
    "TOOL_SCHEMAS",
    "get_course_chunk",
    "list_courses",
    "search_course_material",
]
