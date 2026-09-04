"""训练闭环 (E) API schema (DESIGN §4)。

学生端:出题 → 作答 → 批改 → 更新掌握度。
注意:出题/批改响应均不含参考答案(reference_answer 留服务端,防泄题)。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    learner_id: str = "demo_user"
    # 「换一题」时回传本轮已展示过的题目 id,后端选题会跳过它们(真正换题)。
    exclude_ids: list[str] = Field(default_factory=list)


class TrainingQuestion(BaseModel):
    question_id: str
    topic_id: str
    topic_name: str
    prompt: str
    source: str
    difficulty: str = ""  # easy | medium | hard(自适应出题,前端可显示难度徽标)
    # 无可练知识点时为 True,前端展示空态
    empty: bool = False


class GradeRequest(BaseModel):
    learner_id: str = "demo_user"
    question_id: str
    answer: str


class GradeDimension(BaseModel):
    key: str
    name: str
    weight: float
    score: float


class MasteryUpdate(BaseModel):
    topic_id: str
    level: str
    overwritten: bool = False


class GradeResponse(BaseModel):
    question_id: str
    topic_id: str
    score: float
    passed: bool
    feedback: str
    dimensions: list[GradeDimension] = Field(default_factory=list)
    mastery: MasteryUpdate


# --- 讲师审核沉淀(candidate → approved / rejected,ADR-0006) ---


class CandidateQuestion(BaseModel):
    """待审核候选题。含 reference_answer(仅经讲师守卫路由返回,学生端不可见)。"""

    question_id: str
    topic_id: str
    topic_name: str
    prompt: str
    reference_answer: str
    difficulty: str = ""
    source: str
    created_at: str


class CandidateQuestionList(BaseModel):
    course_pack_id: str
    candidates: list[CandidateQuestion] = Field(default_factory=list)


class ApproveQuestionResponse(BaseModel):
    question_id: str
    topic_id: str
    approved_by: str


class RejectQuestionResponse(BaseModel):
    question_id: str
    rejected: bool
