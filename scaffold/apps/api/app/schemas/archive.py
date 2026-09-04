"""我的学习档案 (Tier 2-6) API schema。

学生登录态查看自己的学习轨迹:掌握度分布 + 练习记录 + 结课项目进度。
数据全部限定在本人 learner_id(路由经 require_learner_id 从 token 解析)。
来源见 apps/api/app/engine/learner_model/service.py:learning_archive。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ArchiveMastery(BaseModel):
    topic_id: str
    name: str
    level: str  # known | fuzzy | unknown
    source: str  # system_inferred | instructor_corrected


class ArchiveLevels(BaseModel):
    known: int = 0
    fuzzy: int = 0
    unknown: int = 0


class ArchiveRecentAttempt(BaseModel):
    topic_id: str
    name: str
    score: float
    created_at: str


class ArchivePractice(BaseModel):
    attempts: int = 0
    avg_score: float | None = None
    recent: list[ArchiveRecentAttempt] = Field(default_factory=list)


class ArchiveMilestone(BaseModel):
    milestone_id: str
    status: str  # not_started | in_progress | passed


class ArchiveCapstone(BaseModel):
    has_project: bool = False
    goal: str = ""
    passed: int = 0
    total: int = 0
    milestones: list[ArchiveMilestone] = Field(default_factory=list)


class LearningArchiveResponse(BaseModel):
    learner_id: str
    course_pack_id: str
    levels: ArchiveLevels
    topics_tracked: int = 0
    masteries: list[ArchiveMastery] = Field(default_factory=list)
    practice: ArchivePractice
    capstone: ArchiveCapstone
