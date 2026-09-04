"""我的学习档案 (Tier 2-6) 路由。

面向登录学生查看自己的学习轨迹(掌握度 / 练习 / 项目进度):
  - GET /api/archive/courses/{course_pack_id}   本人本课程包的学习档案聚合

强制登录(require_learner_id:无 token→401);learner_id 一律取 token 身份,
不接受请求参数指定他人,天然只读自己的数据(不越权)。
领域无关:知识点/里程碑口径来自注入的 CoursePack,只认业务库本人数据。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.auth.deps import current_learner_id
from app.core.config import Settings, get_settings
from app.course_pack import CoursePackLoader
from app.engine.learner_model import SqlLearnerModel
from app.persistence import init_business_db
from app.schemas.archive import LearningArchiveResponse

router = APIRouter(prefix="/api/archive", tags=["archive"])


def require_learner_id(learner_id: str | None = Depends(current_learner_id)) -> str:
    """强制登录:无合法 token → 401。"""
    if not learner_id:
        raise HTTPException(status_code=401, detail="unauthorized: 需要登录")
    return learner_id


@router.get("/courses/{course_pack_id}", response_model=LearningArchiveResponse)
def learning_archive(
    course_pack_id: str,
    learner_id: str = Depends(require_learner_id),
    settings: Settings = Depends(get_settings),
) -> LearningArchiveResponse:
    try:
        pack = CoursePackLoader().load(course_pack_id)
    except Exception as exc:  # 课程包不存在/损坏
        raise HTTPException(
            status_code=404, detail=f"course_pack_not_found: {course_pack_id}"
        ) from exc
    init_business_db(settings)
    model = SqlLearnerModel(pack, settings=settings)
    return LearningArchiveResponse(**model.learning_archive(learner_id, course_pack_id))
