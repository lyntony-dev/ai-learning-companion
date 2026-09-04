"""结课项目 (F) 路由 (DESIGN §4)。

重设计:立项向导 + 个性化清单。面向学生:
  - GET   /api/capstone/courses/{id}/project?learner_id=            读项目状态(无则向导态)
  - POST  /api/capstone/courses/{id}/project                       立项 → 生成项目卡 + 清单
  - PATCH /api/capstone/courses/{id}/project/items/{item_id}       勾选/取消清单项

领域无关:里程碑序列/名称/交付要求来自注入的 CoursePack,技术选型由 LLM 依课程包推断,
零课程硬编码。里程碑状态由清单勾选完成度派生,写回 milestone_progress 供教学洞察聚合。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from app.auth.deps import resolve_learner_id
from app.core.config import Settings, get_settings
from app.course_pack import CoursePackLoader
from app.engine.capstone import SqlCapstoneService
from app.engine.retrieval import VectorStoreRetriever
from app.llm import get_llm_client
from app.persistence import init_business_db
from app.schemas.capstone import (
    CapstoneProjectResponse,
    CreateProjectRequest,
    ToggleItemRequest,
)

router = APIRouter(prefix="/api/capstone", tags=["capstone"])


def get_capstone_service(
    course_pack_id: str,
    settings: Settings = Depends(get_settings),
) -> SqlCapstoneService:
    """按 course_pack_id 构造项目服务;课程包不存在 → 404。"""
    try:
        pack = CoursePackLoader().load(course_pack_id)
    except Exception as exc:  # 课程包不存在/损坏
        raise HTTPException(status_code=404, detail=f"course_pack_not_found: {course_pack_id}") from exc
    init_business_db(settings)
    return SqlCapstoneService(pack, llm=get_llm_client(settings), settings=settings)


@router.get("/courses/{course_pack_id}/project", response_model=CapstoneProjectResponse)
def get_project(
    course_pack_id: str,
    learner_id: str = "demo_user",
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    service: SqlCapstoneService = Depends(get_capstone_service),
) -> CapstoneProjectResponse:
    learner_id = resolve_learner_id(learner_id, authorization, settings)
    return CapstoneProjectResponse(**service.get_project(learner_id, course_pack_id))


@router.post("/courses/{course_pack_id}/project", response_model=CapstoneProjectResponse)
def create_project(
    course_pack_id: str,
    payload: CreateProjectRequest,
    authorization: str | None = Header(default=None),
    service: SqlCapstoneService = Depends(get_capstone_service),
    settings: Settings = Depends(get_settings),
) -> CapstoneProjectResponse:
    learner_id = resolve_learner_id(payload.learner_id, authorization, settings)
    result = service.create_project(
        learner_id=learner_id,
        course_pack_id=course_pack_id,
        goal=payload.goal,
        audience=payload.audience,
        difficulty=payload.difficulty,
        retriever=VectorStoreRetriever(settings),
    )
    return CapstoneProjectResponse(**result)


@router.patch(
    "/courses/{course_pack_id}/project/items/{item_id}",
    response_model=CapstoneProjectResponse,
)
def toggle_item(
    course_pack_id: str,
    item_id: str,
    payload: ToggleItemRequest,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    service: SqlCapstoneService = Depends(get_capstone_service),
) -> CapstoneProjectResponse:
    learner_id = resolve_learner_id(payload.learner_id, authorization, settings)
    try:
        result = service.toggle_item(
            learner_id, course_pack_id, item_id, payload.checked
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CapstoneProjectResponse(**result)
