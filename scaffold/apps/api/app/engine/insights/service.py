"""教学洞察服务 (T) (DESIGN §4 / ADR-0005)。

面向讲师的只读聚合 + 掌握度人工修正:
  - course_insights:对业务库按 topic_id / milestone GROUP BY 聚合,统计各知识点
    的掌握度分布(known/fuzzy/unknown 人数)、做题平均分、里程碑达标分布。
  - learner_profile:单个学员的掌握度档案(只读)。
  - correct_mastery:讲师修正某学员某知识点掌握度(source=INSTRUCTOR_CORRECTED,
    记 updated_by);这是掌握度的最高优先级来源,系统推断(B/E)不覆盖它。

领域无关:知识点/里程碑口径来自注入的 CoursePack,统计只认业务库数据字段。
只针对单个课程(course_pack),不做班级维度(CONTEXT 口径)。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlmodel import select

from app.course_pack.schema import CoursePack
from app.persistence import (
    CapstoneProject,
    ExerciseAttempt,
    Learner,
    Mastery,
    MasteryLevel,
    MasterySource,
    MilestoneProgress,
    MilestoneStatus,
    QaHistory,
    get_session,
)


class LearnerNotFoundError(LookupError):
    """按 learner_id 查不到 Learner 身份主体(避免对不存在的学员假装返回空档案)。"""

    def __init__(self, learner_id: str) -> None:
        super().__init__(f"learner_not_found: {learner_id}")
        self.learner_id = learner_id


class SqlInsightsService:
    """SQLModel 业务库只读聚合 + 讲师修正。持有 CoursePack 以对齐口径。"""

    def __init__(self, course_pack: CoursePack, settings=None) -> None:
        self._pack = course_pack
        self._settings = settings

    # --- 只读聚合 ---

    def _topic_meta(self) -> dict[str, dict]:
        return {
            t.id: {"name": t.name, "course_id": t.course_id}
            for t in self._pack.taxonomy.topics
        }

    def course_insights(self, course_pack_id: str) -> dict:
        """按 topic_id / milestone 聚合的教学洞察(只读)。"""
        from app.auth.service import STUDENT_PREFIX

        topic_meta = self._topic_meta()
        valid_topics = set(topic_meta)

        with get_session(self._settings) as session:
            # 掌握度分布:GROUP BY topic_id, level
            mastery_rows = session.exec(
                select(Mastery.topic_id, Mastery.level, func.count()).group_by(
                    Mastery.topic_id, Mastery.level
                )
            ).all()
            # 做题平均分与次数:GROUP BY topic_id
            attempt_rows = session.exec(
                select(
                    ExerciseAttempt.topic_id,
                    func.avg(ExerciseAttempt.score),
                    func.count(),
                ).group_by(ExerciseAttempt.topic_id)
            ).all()
            # 里程碑达标分布:GROUP BY milestone, status
            milestone_rows = session.exec(
                select(
                    MilestoneProgress.milestone,
                    MilestoneProgress.status,
                    func.count(),
                )
                .where(MilestoneProgress.course_pack_id == course_pack_id)
                .group_by(MilestoneProgress.milestone, MilestoneProgress.status)
            ).all()
            learner_count = session.exec(
                select(func.count())
                .select_from(Learner)
                .where(Learner.learner_id.startswith(STUDENT_PREFIX))
            ).one()

        # 组装 per-topic(只保留本课程包 taxonomy 内的知识点)
        topics: dict[str, dict] = {}
        for tid, level, count in mastery_rows:
            if tid not in valid_topics:
                continue
            entry = topics.setdefault(
                tid,
                {
                    "topic_id": tid,
                    "name": topic_meta[tid]["name"],
                    "course_id": topic_meta[tid]["course_id"],
                    "known": 0,
                    "fuzzy": 0,
                    "unknown": 0,
                    "attempts": 0,
                    "avg_score": None,
                },
            )
            entry[level.value] = int(count)
        for tid, avg_score, cnt in attempt_rows:
            if tid not in valid_topics:
                continue
            entry = topics.setdefault(
                tid,
                {
                    "topic_id": tid,
                    "name": topic_meta[tid]["name"],
                    "course_id": topic_meta[tid]["course_id"],
                    "known": 0,
                    "fuzzy": 0,
                    "unknown": 0,
                    "attempts": 0,
                    "avg_score": None,
                },
            )
            entry["attempts"] = int(cnt)
            entry["avg_score"] = round(float(avg_score), 4) if avg_score is not None else None

        # 薄弱知识点排行(unknown+fuzzy 人数降序)——讲师优先关注
        weak_ranking = sorted(
            topics.values(),
            key=lambda e: (e["unknown"] + e["fuzzy"]),
            reverse=True,
        )

        milestones: dict[str, dict] = {}
        for mid, status, count in milestone_rows:
            entry = milestones.setdefault(
                mid,
                {"milestone": mid, "not_started": 0, "in_progress": 0, "passed": 0},
            )
            entry[status.value] = int(count)

        return {
            "course_pack_id": course_pack_id,
            "learner_count": int(learner_count),
            "topics": [topics[t.id] for t in self._pack.taxonomy.topics if t.id in topics],
            "weak_ranking": weak_ranking,
            "milestones": [
                milestones[m] for m in self._pack.milestone_ids() if m in milestones
            ],
        }

    def north_star_metrics(self, course_pack_id: str) -> dict:
        """北极星指标(只读聚合)。全部取自业务库真实数据,无埋点即为 0,不臆造。

        - engagement:活跃学员数 / 问答轮次 / 练习次数(产品被用起来没有)
        - honesty:证据不足拒答率(诚实铁律的量化,拒答是特性不是失败)
        - mastery_progress:已掌握知识点占比(学得怎么样)
        - practice_quality:练习平均分
        - capstone_funnel:立项数 / 结课数(北极星:把学生带到能交付项目)
        领域无关:只统计业务库字段,知识点/里程碑口径来自注入 CoursePack。
        """
        valid_topics = set(self._pack.topic_ids())
        from app.auth.service import STUDENT_PREFIX

        with get_session(self._settings) as session:
            learner_count = session.exec(
                select(func.count())
                .select_from(Learner)
                .where(Learner.learner_id.startswith(STUDENT_PREFIX))
            ).one()

            qa_total = session.exec(
                select(func.count()).select_from(QaHistory).where(
                    QaHistory.course_pack_id == course_pack_id
                )
            ).one()
            qa_refused = session.exec(
                select(func.count()).select_from(QaHistory).where(
                    QaHistory.course_pack_id == course_pack_id,
                    QaHistory.refused == True,  # noqa: E712 (SQL 布尔列比较)
                )
            ).one()

            attempt_total = session.exec(
                select(func.count()).select_from(ExerciseAttempt)
            ).one()
            attempt_avg = session.exec(
                select(func.avg(ExerciseAttempt.score))
            ).one()

            mastery_rows = session.exec(
                select(Mastery.topic_id, Mastery.level)
            ).all()

            capstone_total = session.exec(
                select(func.count()).select_from(CapstoneProject).where(
                    CapstoneProject.course_pack_id == course_pack_id
                )
            ).one()

            # 结课 = 该项目全部里程碑 passed(与项目陪练 all_passed 口径一致)
            milestone_ids = self._pack.milestone_ids()
            passed_rows = session.exec(
                select(MilestoneProgress.learner_id, func.count()).where(
                    MilestoneProgress.course_pack_id == course_pack_id,
                    MilestoneProgress.status == MilestoneStatus.PASSED,
                ).group_by(MilestoneProgress.learner_id)
            ).all()

        # 掌握度:只认 taxonomy 内知识点
        mastery_known = sum(
            1 for tid, level in mastery_rows
            if tid in valid_topics and level == MasteryLevel.KNOWN
        )
        mastery_tracked = sum(1 for tid, _ in mastery_rows if tid in valid_topics)

        completed = 0
        if milestone_ids:
            need = len(milestone_ids)
            completed = sum(1 for _lid, cnt in passed_rows if int(cnt) >= need)

        qa_total_i = int(qa_total)
        qa_refused_i = int(qa_refused)
        attempt_total_i = int(attempt_total)
        capstone_total_i = int(capstone_total)

        return {
            "course_pack_id": course_pack_id,
            "engagement": {
                "active_learners": int(learner_count),
                "qa_turns": qa_total_i,
                "practice_attempts": attempt_total_i,
            },
            "honesty": {
                "qa_turns": qa_total_i,
                "refused": qa_refused_i,
                "refusal_rate": round(qa_refused_i / qa_total_i, 4) if qa_total_i else 0.0,
            },
            "mastery_progress": {
                "topics_tracked": mastery_tracked,
                "known": mastery_known,
                "known_rate": round(mastery_known / mastery_tracked, 4) if mastery_tracked else 0.0,
            },
            "practice_quality": {
                "attempts": attempt_total_i,
                "avg_score": round(float(attempt_avg), 4) if attempt_avg is not None else None,
            },
            "capstone_funnel": {
                "kickoff": capstone_total_i,
                "completed": completed,
                "completion_rate": round(completed / capstone_total_i, 4)
                if capstone_total_i
                else 0.0,
            },
        }

    def list_learners(
        self, course_pack_id: str, limit: int = 20, offset: int = 0
    ) -> dict:
        """学员列表(只读,分页)。每人带本课程包 taxonomy 内的掌握度概览计数。

        只列学生(learner_id 以 stu_ 开头);讲师不是学员,排除在外。
        排序:已掌握数降序 → learner_id 升序(活跃/掌握靠前,稳定分页)。
        领域无关:掌握度计数只认注入 CoursePack 的知识点。
        """
        from app.auth.service import STUDENT_PREFIX

        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        valid = set(self._pack.topic_ids())
        with get_session(self._settings) as session:
            total = int(
                session.exec(
                    select(func.count())
                    .select_from(Learner)
                    .where(Learner.learner_id.startswith(STUDENT_PREFIX))
                ).one()
            )
            learner_rows = session.exec(
                select(Learner.learner_id, Learner.display_name)
                .where(Learner.learner_id.startswith(STUDENT_PREFIX))
                .order_by(Learner.created_at, Learner.learner_id)
            ).all()
            mastery_rows = session.exec(
                select(Mastery.learner_id, Mastery.topic_id, Mastery.level)
            ).all()

        # 按学员聚合本课程包内知识点的掌握度分布
        counts: dict[str, dict[str, int]] = {}
        for lid, tid, level in mastery_rows:
            if tid not in valid:
                continue
            c = counts.setdefault(lid, {"known": 0, "fuzzy": 0, "unknown": 0})
            key = level.value if hasattr(level, "value") else str(level)
            if key in c:
                c[key] += 1

        items = []
        for lid, display_name in learner_rows:
            c = counts.get(lid, {"known": 0, "fuzzy": 0, "unknown": 0})
            items.append(
                {
                    "learner_id": lid,
                    "display_name": display_name or "",
                    "known": c["known"],
                    "fuzzy": c["fuzzy"],
                    "unknown": c["unknown"],
                    "tracked_topics": c["known"] + c["fuzzy"] + c["unknown"],
                }
            )
        # 掌握数降序 → learner_id 升序;再按 offset/limit 切页
        items.sort(key=lambda x: (-x["known"], x["learner_id"]))
        page = items[offset : offset + limit]
        return {
            "course_pack_id": course_pack_id,
            "items": page,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def learner_profile(self, learner_id: str, course_pack_id: str) -> dict:
        """单学员掌握度档案(只读)。学员不存在 → LearnerNotFoundError。"""
        topic_meta = self._topic_meta()
        valid = set(topic_meta)
        with get_session(self._settings) as session:
            exists = session.exec(
                select(Learner.learner_id).where(Learner.learner_id == learner_id)
            ).first()
            if exists is None:
                raise LearnerNotFoundError(learner_id)
            rows = session.exec(
                select(Mastery).where(Mastery.learner_id == learner_id)
            ).all()
        masteries = [
            {
                "topic_id": r.topic_id,
                "name": topic_meta.get(r.topic_id, {}).get("name", r.topic_id),
                "level": r.level.value,
                "source": r.source.value,
                "updated_by": r.updated_by,
            }
            for r in rows
            if r.topic_id in valid
        ]
        return {
            "learner_id": learner_id,
            "course_pack_id": course_pack_id,
            "masteries": masteries,
        }

    # --- 讲师修正(写:最高优先级来源) ---

    def correct_mastery(
        self,
        learner_id: str,
        topic_id: str,
        level: MasteryLevel,
        updated_by: str,
    ) -> dict:
        """讲师修正掌握度。标 INSTRUCTOR_CORRECTED + updated_by;幂等 upsert。"""
        if topic_id not in set(self._pack.topic_ids()):
            raise ValueError(f"topic_id 不在课程包 taxonomy 内: {topic_id}")
        if not updated_by:
            raise ValueError("讲师修正必须提供 updated_by")

        with get_session(self._settings) as session:
            if session.get(Learner, learner_id) is None:
                session.add(Learner(learner_id=learner_id))
            row = session.exec(
                select(Mastery).where(
                    Mastery.learner_id == learner_id, Mastery.topic_id == topic_id
                )
            ).first()
            if row is None:
                row = Mastery(
                    learner_id=learner_id,
                    topic_id=topic_id,
                    level=level,
                    source=MasterySource.INSTRUCTOR_CORRECTED,
                    updated_by=updated_by,
                    updated_at=datetime.utcnow(),
                )
            else:
                row.level = level
                row.source = MasterySource.INSTRUCTOR_CORRECTED
                row.updated_by = updated_by
                row.updated_at = datetime.utcnow()
            session.add(row)
            session.commit()

        return {
            "learner_id": learner_id,
            "topic_id": topic_id,
            "level": level.value,
            "source": MasterySource.INSTRUCTOR_CORRECTED.value,
            "updated_by": updated_by,
        }
