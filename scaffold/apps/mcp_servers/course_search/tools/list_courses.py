from schemas.course import Course, ListCoursesResponse
from storage import CourseSearchStore

MOCK_COURSES = [
    Course(
        course_id="ppt2_langgraph",
        course_name="PPT2：LangGraph 与多 Agent",
        version="v1",
        tags=["LangGraph", "Agent", "State"],
    ),
    Course(
        course_id="ppt3_mcp",
        course_name="PPT3：MCP 与 Agent 工具生态",
        version="v1",
        tags=["MCP", "Tool Use", "Agent"],
    ),
]


def list_courses(store: CourseSearchStore | None = None) -> ListCoursesResponse:
    course_store = store or CourseSearchStore()
    if course_store.is_available():
        return ListCoursesResponse(courses=course_store.list_courses())
    return ListCoursesResponse(courses=MOCK_COURSES)
