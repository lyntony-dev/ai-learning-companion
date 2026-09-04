"""教学洞察 (T):per-course 只读聚合 + 讲师修正掌握度。"""

from app.engine.insights.service import LearnerNotFoundError, SqlInsightsService

__all__ = ["SqlInsightsService", "LearnerNotFoundError"]
