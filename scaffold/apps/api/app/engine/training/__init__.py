"""训练闭环 (E):出题 / 批改 / 更新掌握度。"""

from app.engine.training.seed import preset_question_id, seed_question_bank
from app.engine.training.service import (
    SqlTrainingService,
    TrainingService,
)

__all__ = [
    "TrainingService",
    "SqlTrainingService",
    "seed_question_bank",
    "preset_question_id",
]
