"""feat-002 业务库领域表测试 (ADR-0005)。

用临时 SQLite 文件验证:建表幂等、六表可写读、枚举往返、外键、
以及教学洞察(T)的 per-course `GROUP BY topic_id` 聚合形态成立。
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.config import Settings
from app.persistence import (
    ExerciseAttempt,
    Learner,
    Mastery,
    MasteryLevel,
    MasterySource,
    MilestoneProgress,
    MilestoneStatus,
    QaHistory,
    QuestionBank,
    QuestionSource,
    get_engine,
    init_business_db,
    reset_engine,
)


@pytest.fixture()
def engine(tmp_path) -> Iterator[object]:
    db_file = tmp_path / "business_test.sqlite"
    settings = Settings(
        _env_file=None,
        BUSINESS_DB_URL=f"sqlite:///{db_file}",
    )
    reset_engine()
    eng = init_business_db(settings)
    yield eng
    reset_engine()


def test_init_is_idempotent(engine) -> None:
    # 再次建表不应报错
    init_business_db()
    assert engine is get_engine()


def test_six_tables_write_read(engine) -> None:
    with Session(engine) as s:
        s.add(Learner(learner_id="stu-1", display_name="小明"))
        s.add(
            Mastery(
                learner_id="stu-1",
                topic_id="langgraph.state",
                level=MasteryLevel.FUZZY,
                source=MasterySource.SYSTEM_INFERRED,
            )
        )
        s.add(
            MilestoneProgress(
                learner_id="stu-1",
                course_pack_id="ai_agent",
                milestone="core_loop",
                status=MilestoneStatus.IN_PROGRESS,
            )
        )
        s.add(
            QuestionBank(
                question_id="q-1",
                course_pack_id="ai_agent",
                topic_id="langgraph.state",
                prompt="什么是 conditional edge?",
                source=QuestionSource.PRESET,
                approved_by="teacher-a",
            )
        )
        s.add(
            ExerciseAttempt(
                learner_id="stu-1",
                question_id="q-1",
                topic_id="langgraph.state",
                score=0.7,
            )
        )
        s.add(
            QaHistory(
                learner_id="stu-1",
                course_pack_id="ai_agent",
                question="RAG 是什么?",
                answer_summary="检索增强生成...",
                topic_ids_json='["rag.basics"]',
            )
        )
        s.commit()

    with Session(engine) as s:
        m = s.exec(select(Mastery).where(Mastery.learner_id == "stu-1")).one()
        assert m.level is MasteryLevel.FUZZY
        assert m.source is MasterySource.SYSTEM_INFERRED
        mp = s.exec(select(MilestoneProgress)).one()
        assert mp.status is MilestoneStatus.IN_PROGRESS
        assert mp.artifact_summary == ""  # V2 占位
        q = s.exec(select(QuestionBank)).one()
        assert q.source is QuestionSource.PRESET
        assert q.approved_by == "teacher-a"


def test_instructor_correction_overwrites_source(engine) -> None:
    with Session(engine) as s:
        s.add(Learner(learner_id="stu-2"))
        s.add(
            Mastery(
                learner_id="stu-2",
                topic_id="mcp.tools",
                level=MasteryLevel.UNKNOWN,
                source=MasterySource.SYSTEM_INFERRED,
            )
        )
        s.commit()
    # 讲师修正
    with Session(engine) as s:
        m = s.exec(select(Mastery).where(Mastery.learner_id == "stu-2")).one()
        m.level = MasteryLevel.KNOWN
        m.source = MasterySource.INSTRUCTOR_CORRECTED
        m.updated_by = "teacher-a"
        s.add(m)
        s.commit()
    with Session(engine) as s:
        m = s.exec(select(Mastery).where(Mastery.learner_id == "stu-2")).one()
        assert m.level is MasteryLevel.KNOWN
        assert m.source is MasterySource.INSTRUCTOR_CORRECTED
        assert m.updated_by == "teacher-a"


def test_per_course_topic_aggregation(engine) -> None:
    """教学洞察(T) per-course 聚合:GROUP BY topic_id 统计薄弱人数。"""
    with Session(engine) as s:
        for i in range(3):
            s.add(Learner(learner_id=f"u{i}"))
        # topic A: 2 人 unknown, topic B: 1 人 fuzzy
        s.add(Mastery(learner_id="u0", topic_id="A", level=MasteryLevel.UNKNOWN))
        s.add(Mastery(learner_id="u1", topic_id="A", level=MasteryLevel.UNKNOWN))
        s.add(Mastery(learner_id="u2", topic_id="B", level=MasteryLevel.FUZZY))
        s.commit()

    with Session(engine) as s:
        rows = s.exec(
            select(Mastery.topic_id, func.count())
            .where(Mastery.level == MasteryLevel.UNKNOWN)
            .group_by(Mastery.topic_id)
        ).all()
        agg = dict(rows)
        assert agg["A"] == 2
        assert "B" not in agg
