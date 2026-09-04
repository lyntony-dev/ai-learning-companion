"""引擎业务库领域模型 (SQLModel, ADR-0005 / DESIGN §5)。

领域无关引擎的持久化实体:学习者档案、掌握度、里程碑、做题、题库、问答历史。
不含任何 AI Agent 课程专属硬编码;course_pack_id / topic_id 均为数据字段。

与脚手架的 RAG/对话/trace 库(原生 sqlite3, migrations/001_initial_schema.sql)物理分离,
本模块独立走 BUSINESS_DB_URL(见 app/persistence/db.py)。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.utcnow()


# --- 枚举 ---


class MasteryLevel(str, Enum):
    """掌握度等级(CONTEXT: 会/模糊/不会)。"""

    KNOWN = "known"
    FUZZY = "fuzzy"
    UNKNOWN = "unknown"


class MasterySource(str, Enum):
    """掌握度来源:系统推断 或 讲师修正(ADR-0005: source/updated_by)。"""

    SYSTEM_INFERRED = "system_inferred"
    INSTRUCTOR_CORRECTED = "instructor_corrected"


class MilestoneStatus(str, Enum):
    """里程碑状态(CONTEXT: 未开始/进行中/已达标)。"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"


class QuestionSource(str, Enum):
    """题目来源:预置题库 或 LLM 依证据生成(CONTEXT 出题策略)。"""

    PRESET = "preset"
    LLM_GENERATED = "llm_generated"


# --- 领域表 ---


class Learner(SQLModel, table=True):
    """学习者身份(跨会话持久主体)。"""

    __tablename__ = "learner"

    learner_id: str = Field(primary_key=True)
    display_name: str = Field(default="")
    created_at: datetime = Field(default_factory=_utcnow)


class LearnerAuth(SQLModel, table=True):
    """学生登录凭据(ADR-0008)。与 Learner 一对一,password_hash 走 bcrypt。

    独立于 Learner 表:身份主体(learner_id)可由访客态/系统创建,登录凭据仅注册用户才有。
    """

    __tablename__ = "learner_auth"

    learner_id: str = Field(foreign_key="learner.learner_id", primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str = Field(default="")
    created_at: datetime = Field(default_factory=_utcnow)


class LearnerProfile(SQLModel, table=True):
    """学生画像(ADR-0008)。基础资料 + 学习目标与偏好;自动画像(掌握度)运行时聚合不入此表。

    与 Learner 一对一。登录后可查看/更新;字段均可空,渐进填写。
    """

    __tablename__ = "learner_profile"

    learner_id: str = Field(foreign_key="learner.learner_id", primary_key=True)
    nickname: str = Field(default="")  # 基础资料:昵称
    avatar: str = Field(default="")  # 基础资料:头像(emoji 或 url)
    background: str = Field(default="")  # 基础资料:背景自述(如"后端工程师,想转 AI")
    learning_goal: str = Field(default="")  # 学习目标(自由文本)
    weekly_hours: int = Field(default=0)  # 每周投入时间(小时)
    preferred_difficulty: str = Field(default="")  # 期望难度偏好
    updated_at: datetime = Field(default_factory=_utcnow)



class Mastery(SQLModel, table=True):
    """掌握度:按 (learner, topic) 建行。source 区分系统推断/讲师修正。"""

    __tablename__ = "mastery"

    id: int | None = Field(default=None, primary_key=True)
    learner_id: str = Field(foreign_key="learner.learner_id", index=True)
    topic_id: str = Field(index=True)
    level: MasteryLevel = Field(default=MasteryLevel.UNKNOWN)
    source: MasterySource = Field(default=MasterySource.SYSTEM_INFERRED)
    updated_by: str = Field(default="")  # 讲师修正时记修正者
    updated_at: datetime = Field(default_factory=_utcnow)


class MilestoneProgress(SQLModel, table=True):
    """结课项目里程碑状态机(F)。artifact_summary 为 V2 产出物接入预留。

    状态由 CapstoneProject 的清单勾选完成度派生写回(全勾→passed / 部分→in_progress),
    供教学洞察(T)里程碑漏斗聚合。
    """

    __tablename__ = "milestone_progress"

    id: int | None = Field(default=None, primary_key=True)
    learner_id: str = Field(foreign_key="learner.learner_id", index=True)
    course_pack_id: str = Field(index=True)
    milestone: str = Field(index=True)
    status: MilestoneStatus = Field(default=MilestoneStatus.NOT_STARTED)
    artifact_summary: str = Field(default="")  # V2: 真实产出物接入占位
    updated_at: datetime = Field(default_factory=_utcnow)


class CapstoneProject(SQLModel, table=True):
    """结课项目立项 + 个性化清单(F)。

    一个 (learner, course_pack) 一行。学生立项(goal/audience/difficulty)后,
    引擎基于课程包 + RAG 生成项目卡(card_json:title/scope/tech_stack)与每个里程碑的
    可勾选清单(checklist_json:{milestone_id: [{id,text,checked}]}),把"满足需要"的标准
    绑定到学生自己的项目上。里程碑状态从清单勾选完成度派生,写回 MilestoneProgress。
    """

    __tablename__ = "capstone_project"

    id: int | None = Field(default=None, primary_key=True)
    learner_id: str = Field(foreign_key="learner.learner_id", index=True)
    course_pack_id: str = Field(index=True)
    goal: str = Field(default="")  # 立项:想做什么 Agent
    audience: str = Field(default="")  # 立项:面向谁/什么场景
    difficulty: str = Field(default="")  # 立项:预期难点(选填)
    card_json: str = Field(default="{}")  # 项目卡:{title, scope, tech_stack:[...]}
    checklist_json: str = Field(default="{}")  # {milestone_id: [{id, text, checked}]}
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ExerciseAttempt(SQLModel, table=True):
    """做题结果(E)。反哺掌握度与教学洞察。"""

    __tablename__ = "exercise_attempt"

    id: int | None = Field(default=None, primary_key=True)
    learner_id: str = Field(foreign_key="learner.learner_id", index=True)
    question_id: str = Field(foreign_key="question_bank.question_id", index=True)
    topic_id: str = Field(index=True)
    score: float = Field(default=0.0)
    feedback: str = Field(default="")
    created_at: datetime = Field(default_factory=_utcnow)


class QuestionBank(SQLModel, table=True):
    """题库(E)。source 区分预置/LLM 生成;approved_by 支撑讲师审核沉淀飞轮。"""

    __tablename__ = "question_bank"

    question_id: str = Field(primary_key=True)
    course_pack_id: str = Field(index=True)
    topic_id: str = Field(index=True)
    prompt: str = Field(default="")
    reference_answer: str = Field(default="")
    difficulty: str = Field(default="medium")  # easy | medium | hard(自适应出题用)
    source: QuestionSource = Field(default=QuestionSource.PRESET)
    approved_by: str = Field(default="")  # 空=候选;非空=讲师已审核沉淀
    created_at: datetime = Field(default_factory=_utcnow)


class QaHistory(SQLModel, table=True):
    """问答历史(Learner Model 组成部分)。"""

    __tablename__ = "qa_history"

    id: int | None = Field(default=None, primary_key=True)
    learner_id: str = Field(foreign_key="learner.learner_id", index=True)
    course_pack_id: str = Field(index=True)
    question: str = Field(default="")
    answer_summary: str = Field(default="")
    topic_ids_json: str = Field(default="[]")  # 涉及知识点
    refused: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utcnow)
