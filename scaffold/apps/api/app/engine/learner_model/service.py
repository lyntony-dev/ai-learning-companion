"""Learner Model — 掌握度读写与推断 (B) (DESIGN §4 / ADR-0005)。

职责:
  - 读:给 C 画像装饰提供 mastery_profile 与 weak_topics(检索扩展/答复深浅)。
  - 写:问答触发后,把本轮涉及的知识点与结果沉淀到 mastery / qa_history。

领域无关:知识点集合来自注入的 CoursePack.taxonomy,不硬编码任何课程内容。
掌握度语义(CONTEXT):
  - 问答仅是"接触"证据,最高只把知识点标到 fuzzy(接触过但未经练习验证)。
  - KNOWN 只由训练闭环(E, feat-007)按 Rubric 批改产生。
  - 讲师修正(instructor_corrected)优先级最高,系统推断不覆盖它。
"""

from __future__ import annotations

import json
from typing import Protocol

from sqlmodel import select

from app.course_pack.schema import CoursePack
from app.persistence import (
    CapstoneProject,
    ExerciseAttempt,
    Learner,
    LearnerProfile,
    Mastery,
    MasteryLevel,
    MasterySource,
    MilestoneProgress,
    MilestoneStatus,
    QaHistory,
    get_session,
)


class LearnerModel(Protocol):
    """引擎编排层依赖的 Learner Model 读写面(可注入替身)。"""

    def profile(self, learner_id: str, course_pack_id: str) -> dict: ...

    def weak_topics(self, learner_id: str, course_pack_id: str) -> list[str]: ...

    def learner_profile(self, learner_id: str) -> dict: ...

    def record_qa_turn(self, state: dict) -> dict: ...


class EmptyLearnerModel:
    """无持久化占位(新学员/离线)。read 返回空,write 为 no-op。"""

    def profile(self, learner_id: str, course_pack_id: str) -> dict:
        return {}

    def weak_topics(self, learner_id: str, course_pack_id: str) -> list[str]:
        return []

    def learner_profile(self, learner_id: str) -> dict:
        return {}

    def record_qa_turn(self, state: dict) -> dict:
        return {"touched_topics": [], "mastery_updates": 0}


def _tokenize(text: str) -> set[str]:
    lowered = text.lower()
    for ch in "，。！？、；：（）()[]{}<>“”\"'`,.!?;:/\\|":
        lowered = lowered.replace(ch, " ")
    return {t for t in lowered.split() if t}


class SqlLearnerModel:
    """SQLModel 业务库实现。持有 CoursePack 以做数据驱动的知识点匹配。"""

    def __init__(self, course_pack: CoursePack, settings=None) -> None:
        self._pack = course_pack
        self._settings = settings

    # --- 读:C 画像 ---

    def profile(self, learner_id: str, course_pack_id: str) -> dict:
        with get_session(self._settings) as session:
            rows = session.exec(
                select(Mastery).where(Mastery.learner_id == learner_id)
            ).all()
        # 只暴露本课程包 taxonomy 内的知识点
        valid = set(self._pack.topic_ids())
        return {r.topic_id: r.level.value for r in rows if r.topic_id in valid}

    def weak_topics(self, learner_id: str, course_pack_id: str) -> list[str]:
        prof = self.profile(learner_id, course_pack_id)
        weak = {MasteryLevel.UNKNOWN.value, MasteryLevel.FUZZY.value}
        return [tid for tid, level in prof.items() if level in weak]

    def learner_profile(self, learner_id: str) -> dict:
        """读学员自述画像(背景/目标/偏好难度),供 C 个性化装饰用。

        领域无关:这些是**学员**属性,非课程内容;不存在则返回空 dict。
        """
        with get_session(self._settings) as session:
            row = session.get(LearnerProfile, learner_id)
        if row is None:
            return {}
        return {
            "background": row.background,
            "learning_goal": row.learning_goal,
            "preferred_difficulty": row.preferred_difficulty,
        }

    def learning_archive(self, learner_id: str, course_pack_id: str) -> dict:
        """我的学习档案:按 learner_id 聚合本课程包的掌握度 / 练习 / 项目进度(只读)。

        面向登录学生看自己的学习轨迹,数据全部限定在本人 learner_id:
          - mastery:本课程包 taxonomy 内各知识点当前掌握度(含来源,讲师修正可见)
          - practice:做题次数 / 平均分 / 最近若干次记录(反哺信心与复盘)
          - capstone:结课项目立项与里程碑达标进度(未立项则 has_project=False)
        领域无关:知识点/里程碑口径来自注入的 CoursePack,只认业务库本人数据。
        """
        topic_meta = {t.id: t.name for t in self._pack.taxonomy.topics}
        valid = set(topic_meta)
        milestone_ids = self._pack.milestone_ids()

        with get_session(self._settings) as session:
            mastery_rows = session.exec(
                select(Mastery).where(Mastery.learner_id == learner_id)
            ).all()
            attempt_rows = session.exec(
                select(ExerciseAttempt)
                .where(ExerciseAttempt.learner_id == learner_id)
                .order_by(ExerciseAttempt.created_at.desc())  # type: ignore[attr-defined]
            ).all()
            milestone_rows = session.exec(
                select(MilestoneProgress).where(
                    MilestoneProgress.learner_id == learner_id,
                    MilestoneProgress.course_pack_id == course_pack_id,
                )
            ).all()
            project = session.exec(
                select(CapstoneProject).where(
                    CapstoneProject.learner_id == learner_id,
                    CapstoneProject.course_pack_id == course_pack_id,
                )
            ).first()

        masteries = [
            {
                "topic_id": r.topic_id,
                "name": topic_meta.get(r.topic_id, r.topic_id),
                "level": r.level.value,
                "source": r.source.value,
            }
            for r in mastery_rows
            if r.topic_id in valid
        ]
        levels = {"known": 0, "fuzzy": 0, "unknown": 0}
        for m in masteries:
            if m["level"] in levels:
                levels[m["level"]] += 1

        scores = [a.score for a in attempt_rows]
        practice = {
            "attempts": len(attempt_rows),
            "avg_score": round(sum(scores) / len(scores), 4) if scores else None,
            "recent": [
                {
                    "topic_id": a.topic_id,
                    "name": topic_meta.get(a.topic_id, a.topic_id),
                    "score": a.score,
                    "created_at": a.created_at.isoformat(),
                }
                for a in attempt_rows[:5]
            ],
        }

        status_by_ms = {r.milestone: r.status for r in milestone_rows}
        passed = sum(1 for s in status_by_ms.values() if s == MilestoneStatus.PASSED)
        capstone = {
            "has_project": project is not None,
            "goal": project.goal if project else "",
            "passed": passed,
            "total": len(milestone_ids),
            "milestones": [
                {
                    "milestone_id": mid,
                    "status": status_by_ms.get(mid, MilestoneStatus.NOT_STARTED).value,
                }
                for mid in milestone_ids
            ],
        }

        return {
            "learner_id": learner_id,
            "course_pack_id": course_pack_id,
            "levels": levels,
            "topics_tracked": len(masteries),
            "masteries": masteries,
            "practice": practice,
            "capstone": capstone,
        }

    # --- 写:B 掌握度更新 + 问答历史 ---

    def match_topics(self, query: str, chunks: list[dict]) -> list[str]:
        """把一次问答关联到 taxonomy 知识点(名称 token 命中 query 或检索文本)。"""
        haystack = _tokenize(query)
        for c in chunks[:3]:
            haystack |= _tokenize(c.get("text", ""))
        # 命中的 course_id(缩小候选到被检索到的课程)
        hit_courses = {c.get("metadata", {}).get("course_id") for c in chunks}
        matched: list[str] = []
        for topic in self._pack.taxonomy.topics:
            if hit_courses and topic.course_id not in hit_courses:
                continue
            name_tokens = _tokenize(topic.name) | _tokenize(topic.id.replace(".", " "))
            if name_tokens & haystack:
                matched.append(topic.id)
        return matched

    def record_qa_turn(self, state: dict) -> dict:
        learner_id = state.get("learner_id", "")
        course_pack_id = state.get("course_pack_id", "")
        query = state.get("query", "")
        chunks = state.get("retrieved_chunks", [])
        refused = bool(state.get("refused"))

        touched = self.match_topics(query, chunks)
        updates = 0
        with get_session(self._settings) as session:
            # 确保 learner 存在
            if session.get(Learner, learner_id) is None:
                session.add(Learner(learner_id=learner_id))

            # 问答历史
            session.add(
                QaHistory(
                    learner_id=learner_id,
                    course_pack_id=course_pack_id,
                    question=query[:500],
                    answer_summary=state.get("answer", "")[:500],
                    topic_ids_json=json.dumps(touched, ensure_ascii=False),
                    refused=refused,
                )
            )

            # 掌握度推断:接触过的知识点若无记录 → fuzzy;不下调,不覆盖讲师修正
            if not refused:
                existing = {
                    m.topic_id: m
                    for m in session.exec(
                        select(Mastery).where(Mastery.learner_id == learner_id)
                    ).all()
                }
                for tid in touched:
                    m = existing.get(tid)
                    if m is None:
                        session.add(
                            Mastery(
                                learner_id=learner_id,
                                topic_id=tid,
                                level=MasteryLevel.FUZZY,
                                source=MasterySource.SYSTEM_INFERRED,
                            )
                        )
                        updates += 1
                    # 已有记录:问答不提升到 known,也不覆盖讲师修正 → 保持
            session.commit()

        return {"touched_topics": touched, "mastery_updates": updates}
