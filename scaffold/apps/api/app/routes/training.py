"""训练闭环 (E) 路由 (DESIGN §4)。

面向学生:
  - POST /api/training/courses/{course_pack_id}/questions  出题(匹配薄弱知识点)
  - POST /api/training/courses/{course_pack_id}/grade       批改 + 更新掌握度

领域无关:引擎只依赖注入的 CoursePack / 题库 / rubric,零课程硬编码。
出题/批改响应不含参考答案(reference_answer 留服务端,防泄题)。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from app.auth.deps import require_teacher, resolve_learner_id
from app.core.config import Settings, get_settings
from app.course_pack import CoursePackLoader
from app.engine.learner_model import SqlLearnerModel
from app.engine.retrieval import VectorStoreRetriever
from app.engine.training import SqlTrainingService, seed_question_bank
from app.llm import get_llm_client
from app.persistence import init_business_db
from app.schemas.training import (
    ApproveQuestionResponse,
    CandidateQuestion,
    CandidateQuestionList,
    GradeRequest,
    GradeResponse,
    QuestionRequest,
    RejectQuestionResponse,
    TrainingQuestion,
)

router = APIRouter(prefix="/api/training", tags=["training"])


def get_training_service(
    course_pack_id: str,
    settings: Settings = Depends(get_settings),
) -> SqlTrainingService:
    """按 course_pack_id 构造训练服务;课程包不存在 → 404。"""
    try:
        pack = CoursePackLoader().load(course_pack_id)
    except Exception as exc:  # 课程包不存在/损坏
        raise HTTPException(status_code=404, detail=f"course_pack_not_found: {course_pack_id}") from exc
    init_business_db(settings)
    # 幂等地把课程包预置题库沉淀进业务库(非破坏,不触碰 LLM 候选)
    seed_question_bank(pack, settings)
    return SqlTrainingService(pack, llm=get_llm_client(settings), settings=settings)


@router.post("/courses/{course_pack_id}/questions", response_model=TrainingQuestion)
def next_question(
    course_pack_id: str,
    payload: QuestionRequest,
    authorization: str | None = Header(default=None),
    service: SqlTrainingService = Depends(get_training_service),
    settings: Settings = Depends(get_settings),
) -> TrainingQuestion:
    learner_id = resolve_learner_id(payload.learner_id, authorization, settings)
    # 薄弱知识点由 Learner Model 读出(问答/训练沉淀),空则退到课程包首个知识点
    pack = CoursePackLoader().load(course_pack_id)
    learner_model = SqlLearnerModel(pack, settings=settings)
    weak = learner_model.weak_topics(learner_id, course_pack_id)

    question = service.select_question(
        learner_id=learner_id,
        course_pack_id=course_pack_id,
        weak_topics=weak,
        retriever=VectorStoreRetriever(settings),
        exclude_ids=payload.exclude_ids,
    )
    if not question:
        return TrainingQuestion(
            question_id="", topic_id="", topic_name="", prompt="", source="", empty=True
        )
    topic_id = question["topic_id"]
    return TrainingQuestion(
        question_id=question["question_id"],
        topic_id=topic_id,
        topic_name=pack_topic_name(pack, topic_id),
        prompt=question["prompt"],
        source=question["source"],
        difficulty=question.get("difficulty", ""),
    )


@router.post("/courses/{course_pack_id}/grade", response_model=GradeResponse)
def grade_answer(
    course_pack_id: str,
    payload: GradeRequest,
    authorization: str | None = Header(default=None),
    service: SqlTrainingService = Depends(get_training_service),
    settings: Settings = Depends(get_settings),
) -> GradeResponse:
    learner_id = resolve_learner_id(payload.learner_id, authorization, settings)
    # 服务端按 question_id 重载完整题目(含参考答案),不信任前端回传
    question = service.get_question(course_pack_id, payload.question_id)
    if not question:
        raise HTTPException(status_code=404, detail=f"question_not_found: {payload.question_id}")

    grade = service.grade(question, payload.answer)
    mastery = service.update_mastery(learner_id, question, grade)
    return GradeResponse(
        question_id=question["question_id"],
        topic_id=question["topic_id"],
        score=grade["score"],
        passed=grade["passed"],
        feedback=grade["feedback"],
        dimensions=grade["dimensions"],
        mastery={
            "topic_id": mastery["topic_id"],
            "level": mastery["level"],
            "overwritten": mastery["overwritten"],
        },
    )


def pack_topic_name(pack, topic_id: str) -> str:
    t = next((t for t in pack.taxonomy.topics if t.id == topic_id), None)
    return t.name if t else topic_id


# --- 讲师审核沉淀(candidate → approved / rejected,ADR-0006 飞轮) ---
# 均需讲师身份(require_teacher:无 token→401,非讲师→403)。
# 候选题含参考答案,只经讲师守卫返回,学生端出题/批改仍不含 reference_answer。


@router.get(
    "/courses/{course_pack_id}/candidates",
    response_model=CandidateQuestionList,
)
def list_candidates(
    course_pack_id: str,
    service: SqlTrainingService = Depends(get_training_service),
    _teacher: dict = Depends(require_teacher),
) -> CandidateQuestionList:
    candidates = service.list_candidate_questions(course_pack_id)
    return CandidateQuestionList(
        course_pack_id=course_pack_id,
        candidates=[CandidateQuestion(**c) for c in candidates],
    )


@router.post(
    "/courses/{course_pack_id}/candidates/{question_id}/approve",
    response_model=ApproveQuestionResponse,
)
def approve_candidate(
    course_pack_id: str,
    question_id: str,
    service: SqlTrainingService = Depends(get_training_service),
    teacher: dict = Depends(require_teacher),
) -> ApproveQuestionResponse:
    try:
        result = service.approve_question(
            course_pack_id=course_pack_id,
            question_id=question_id,
            # approved_by 以认证讲师为准,不信任请求体(防伪造)
            approved_by=teacher.get("username") or teacher.get("learner_id") or "teacher",
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApproveQuestionResponse(**result)


@router.post(
    "/courses/{course_pack_id}/candidates/{question_id}/reject",
    response_model=RejectQuestionResponse,
)
def reject_candidate(
    course_pack_id: str,
    question_id: str,
    service: SqlTrainingService = Depends(get_training_service),
    _teacher: dict = Depends(require_teacher),
) -> RejectQuestionResponse:
    try:
        result = service.reject_question(course_pack_id, question_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RejectQuestionResponse(**result)
