"""教学洞察 (T) API schema (DESIGN §4)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.persistence import MasteryLevel


class TopicInsight(BaseModel):
    topic_id: str
    name: str
    course_id: str
    known: int = 0
    fuzzy: int = 0
    unknown: int = 0
    attempts: int = 0
    avg_score: float | None = None


class MilestoneInsight(BaseModel):
    milestone: str
    not_started: int = 0
    in_progress: int = 0
    passed: int = 0


class CourseInsightsResponse(BaseModel):
    course_pack_id: str
    learner_count: int
    topics: list[TopicInsight] = Field(default_factory=list)
    weak_ranking: list[TopicInsight] = Field(default_factory=list)
    milestones: list[MilestoneInsight] = Field(default_factory=list)


class MasteryEntry(BaseModel):
    topic_id: str
    name: str
    level: str
    source: str
    updated_by: str = ""


class LearnerProfileResponse(BaseModel):
    learner_id: str
    course_pack_id: str
    masteries: list[MasteryEntry] = Field(default_factory=list)


class LearnerListItem(BaseModel):
    learner_id: str
    display_name: str = ""
    known: int = 0
    fuzzy: int = 0
    unknown: int = 0
    tracked_topics: int = 0


class LearnerListResponse(BaseModel):
    course_pack_id: str
    items: list[LearnerListItem] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0


class MasteryCorrectionRequest(BaseModel):
    learner_id: str
    topic_id: str
    level: MasteryLevel
    updated_by: str = ""  # 已忽略:以认证讲师身份为准(保留字段向后兼容)


class MasteryCorrectionResponse(BaseModel):
    learner_id: str
    topic_id: str
    level: str
    source: str
    updated_by: str


# --- 北极星指标(Tier 3-7)---


class MetricsEngagement(BaseModel):
    active_learners: int = 0
    qa_turns: int = 0
    practice_attempts: int = 0


class MetricsHonesty(BaseModel):
    qa_turns: int = 0
    refused: int = 0
    refusal_rate: float = 0.0


class MetricsMasteryProgress(BaseModel):
    topics_tracked: int = 0
    known: int = 0
    known_rate: float = 0.0


class MetricsPracticeQuality(BaseModel):
    attempts: int = 0
    avg_score: float | None = None


class MetricsCapstoneFunnel(BaseModel):
    kickoff: int = 0
    completed: int = 0
    completion_rate: float = 0.0


class NorthStarMetricsResponse(BaseModel):
    course_pack_id: str
    engagement: MetricsEngagement
    honesty: MetricsHonesty
    mastery_progress: MetricsMasteryProgress
    practice_quality: MetricsPracticeQuality
    capstone_funnel: MetricsCapstoneFunnel
