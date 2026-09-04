"""教学洞察 (T) 路由 (DESIGN §4)。

面向讲师:
  - GET  /api/insights/courses/{course_pack_id}          per-course 聚合(只读)
  - GET  /api/insights/courses/{course_pack_id}/learners  学员列表(只读,分页)
  - GET  /api/insights/courses/{course_pack_id}/learners/{learner_id}  个体档案(只读;不存在→404)
  - POST /api/insights/courses/{course_pack_id}/mastery-corrections     讲师修正掌握度

**均需讲师身份**(require_teacher:无 token→401,非讲师→403)。修正的 updated_by 以
认证讲师身份为准(不信任请求体,防伪造)。
只针对单个课程(course_pack),不做班级维度(CONTEXT 口径)。
掌握度修正标 INSTRUCTOR_CORRECTED,是最高优先级来源,系统推断(B/E)不覆盖。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.deps import require_teacher
from app.core.config import Settings, get_settings
from app.course_pack import CoursePackLoader
from app.engine.insights import LearnerNotFoundError, SqlInsightsService
from app.persistence import init_business_db
from app.schemas.insights import (
    CourseInsightsResponse,
    LearnerListResponse,
    LearnerProfileResponse,
    MasteryCorrectionRequest,
    MasteryCorrectionResponse,
    NorthStarMetricsResponse,
)

router = APIRouter(prefix="/api/insights", tags=["insights"])


def get_insights_service(
    course_pack_id: str,
    settings: Settings = Depends(get_settings),
) -> SqlInsightsService:
    """按 course_pack_id 构造洞察服务;课程包不存在 → 404。"""
    try:
        pack = CoursePackLoader().load(course_pack_id)
    except Exception as exc:  # 课程包不存在/损坏
        raise HTTPException(status_code=404, detail=f"course_pack_not_found: {course_pack_id}") from exc
    init_business_db(settings)
    return SqlInsightsService(pack, settings=settings)


@router.get("/courses/{course_pack_id}", response_model=CourseInsightsResponse)
def course_insights(
    course_pack_id: str,
    service: SqlInsightsService = Depends(get_insights_service),
    _teacher: dict = Depends(require_teacher),
) -> CourseInsightsResponse:
    return CourseInsightsResponse(**service.course_insights(course_pack_id))


@router.get("/courses/{course_pack_id}/metrics", response_model=NorthStarMetricsResponse)
def north_star_metrics(
    course_pack_id: str,
    service: SqlInsightsService = Depends(get_insights_service),
    _teacher: dict = Depends(require_teacher),
) -> NorthStarMetricsResponse:
    """北极星指标(讲师只读):活跃/诚实拒答率/掌握进度/练习质量/结课漏斗。"""
    return NorthStarMetricsResponse(**service.north_star_metrics(course_pack_id))


@router.get(
    "/courses/{course_pack_id}/learners",
    response_model=LearnerListResponse,
)
def list_learners(
    course_pack_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: SqlInsightsService = Depends(get_insights_service),
    _teacher: dict = Depends(require_teacher),
) -> LearnerListResponse:
    """学员列表(讲师只读,分页)。每人带本课程包知识点掌握度概览计数。"""
    return LearnerListResponse(**service.list_learners(course_pack_id, limit, offset))


@router.get(
    "/courses/{course_pack_id}/learners/{learner_id}",
    response_model=LearnerProfileResponse,
)
def learner_profile(
    course_pack_id: str,
    learner_id: str,
    service: SqlInsightsService = Depends(get_insights_service),
    _teacher: dict = Depends(require_teacher),
) -> LearnerProfileResponse:
    try:
        return LearnerProfileResponse(**service.learner_profile(learner_id, course_pack_id))
    except LearnerNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/courses/{course_pack_id}/mastery-corrections",
    response_model=MasteryCorrectionResponse,
)
def correct_mastery(
    course_pack_id: str,
    payload: MasteryCorrectionRequest,
    service: SqlInsightsService = Depends(get_insights_service),
    teacher: dict = Depends(require_teacher),
) -> MasteryCorrectionResponse:
    try:
        result = service.correct_mastery(
            learner_id=payload.learner_id,
            topic_id=payload.topic_id,
            level=payload.level,
            # updated_by 以认证讲师为准,不信任请求体(防伪造)
            updated_by=teacher.get("username") or teacher.get("learner_id") or "teacher",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return MasteryCorrectionResponse(**result)
