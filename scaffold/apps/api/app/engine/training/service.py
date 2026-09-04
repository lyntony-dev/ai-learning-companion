"""训练闭环服务 (E) (DESIGN §4 / ADR-0005/0006)。

一轮训练:出题 → 批改 → 更新掌握度。

职责:
  - select_question:优先取预置题库中匹配薄弱点的题;不足则 LLM 依 RAG 证据生成
    候选题(source=LLM_GENERATED, approved_by="" 待讲师审核,ADR-0006 飞轮)。
  - grade:Grader 按 CoursePack.rubric 维度打分(LLM 产出结构化评分,含启发式回退)。
  - update_mastery:写 exercise_attempt,并按分数回写 mastery。
    与问答(仅到 fuzzy)不同:训练经批改**可达 known**;但不覆盖讲师修正。

领域无关:题目、维度、知识点均来自注入的 CoursePack / 题库,不硬编码课程内容。
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Protocol

from sqlmodel import select

from app.course_pack.schema import CoursePack
from app.persistence import (
    ExerciseAttempt,
    Learner,
    LearnerProfile,
    Mastery,
    MasteryLevel,
    MasterySource,
    QuestionBank,
    QuestionSource,
    get_session,
)
from app.llm import LLMClient, get_llm_client

# 批改结果 → 掌握度阈值(训练闭环可达 known)
KNOWN_SCORE_THRESHOLD = 0.8
FUZZY_SCORE_THRESHOLD = 0.4

_GRADE_SYSTEM = (
    "你是课程作业批改助手。依据评分维度与参考答案,对学员作答逐维打分(0~1)。"
    "只输出 JSON,不要多余文字。"
)

_GRADE_TEMPLATE = """题目: {prompt}
参考答案: {reference}
评分维度: {dimensions}
学员作答: {answer}

请输出 JSON:
{{
  "dimensions": [{{"key": "维度key", "score": 0.0}}],
  "feedback": "一句话反馈,指出得失与改进方向"
}}"""

_GEN_SYSTEM = (
    "你是课程出题助手。只依据给定课程材料出一道考查该知识点的练习题,"
    "不得引入材料之外的其它技术或框架。只输出 JSON。"
)

_GEN_TEMPLATE = """课程: {course_name}
知识点: {topic_name}
目标难度: {difficulty}(easy=概念复述; medium=机制/对比说明; hard=设计/权衡分析)
课程材料片段(出题必须紧扣以下材料,不要跑题到其它框架):
{corpus}

请按目标难度出一道题,输出 JSON:
{{"prompt": "题干(简短明确,紧扣上述课程材料且符合目标难度)", "reference_answer": "参考答案要点"}}"""

# 掌握度 → 目标出题难度(自适应:弱点出简单题建立信心,已会则出难题挑战)
_MASTERY_TO_DIFFICULTY = {
    MasteryLevel.UNKNOWN.value: "easy",
    MasteryLevel.FUZZY.value: "medium",
    MasteryLevel.KNOWN.value: "hard",
}
# 目标难度取不到题时的降级顺序
_DIFFICULTY_FALLBACK = {
    "easy": ["easy", "medium", "hard"],
    "medium": ["medium", "easy", "hard"],
    "hard": ["hard", "medium", "easy"],
}
# 难度序数,用于把「掌握度目标难度」与「学员偏好难度」取偏保守的一侧融合
_DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}
_ORDER_TO_DIFFICULTY = {0: "easy", 1: "medium", 2: "hard"}


class TrainingService(Protocol):
    """训练闭环读写面(可注入替身)。"""

    def select_question(
        self,
        learner_id: str,
        course_pack_id: str,
        weak_topics: list[str],
        retriever=None,
        exclude_ids: list[str] | None = None,
    ) -> dict: ...

    def grade(self, question: dict, learner_answer: str) -> dict: ...

    def update_mastery(self, learner_id: str, question: dict, grade: dict) -> dict: ...

    def get_question(self, course_pack_id: str, question_id: str) -> dict: ...


def _parse_llm_json(raw: str) -> dict:
    """从 LLM 返回稳健抽取 JSON(容忍 ```json 包裹与前后噪声)。"""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


def _tokenize(text: str) -> set[str]:
    lowered = (text or "").lower()
    for ch in "，。！？、；：（）()[]{}<>“”\"'`,.!?;:/\\|":
        lowered = lowered.replace(ch, " ")
    return {t for t in lowered.split() if t}


class SqlTrainingService:
    """SQLModel 业务库实现。持有 CoursePack(rubric/taxonomy)与 LLM。"""

    def __init__(self, course_pack: CoursePack, llm: LLMClient | None = None, settings=None) -> None:
        self._pack = course_pack
        self._llm = llm or get_llm_client(settings)
        self._settings = settings

    # --- 出题 ---

    def _topic_course(self, topic_id: str) -> str:
        t = next((t for t in self._pack.taxonomy.topics if t.id == topic_id), None)
        return t.course_id if t else ""

    def _topic_name(self, topic_id: str) -> str:
        t = next((t for t in self._pack.taxonomy.topics if t.id == topic_id), None)
        return t.name if t else topic_id

    def _ordered_topics(self, weak_topics: list[str]) -> list[str]:
        """出题知识点的候选顺序:薄弱点优先,其后补齐课程包其余知识点。

        用于「换一题」跨知识点轮换——当前知识点的题都练过时,换到下一个知识点,
        而不是在同一知识点里反复给同一道题。领域无关:顺序只由注入 taxonomy 决定。
        """
        valid = self._pack.topic_ids()
        ordered = [tid for tid in weak_topics if tid in valid]
        for tid in valid:
            if tid not in ordered:
                ordered.append(tid)
        return ordered

    def _rubric_dimensions_for(self, topic_id: str) -> list[dict]:
        """按知识点所属课程取评分维度。

        课程有专项配置时:引用的默认维度子集 + 该课额外维度;否则回退全部默认维度。
        (修复历史 bug:旧 by_course_focus 存散文,与维度 key 匹配不上,专项维度从不生效。)
        """
        rubric = self._pack.rubric
        default = {d.key: d for d in rubric.default_dimensions}
        course_id = self._topic_course(topic_id)
        spec = rubric.by_course.get(course_id)
        dims: list = []
        if spec is not None:
            dims = [default[k] for k in spec.dimensions if k in default]
            dims += list(spec.extra_dimensions)
        if not dims:
            dims = list(default.values())
        return [{"key": d.key, "name": d.name, "weight": d.weight or 1.0} for d in dims]

    def _recent_attempt_counts(self, learner_id: str, question_ids: list[str]) -> dict[str, int]:
        """统计学员对候选题的历史作答次数(防重复出题依据)。"""
        if not question_ids:
            return {}
        with get_session(self._settings) as session:
            rows = session.exec(
                select(ExerciseAttempt).where(
                    ExerciseAttempt.learner_id == learner_id,
                    ExerciseAttempt.question_id.in_(question_ids),  # type: ignore[attr-defined]
                )
            ).all()
        counts: dict[str, int] = {}
        for r in rows:
            counts[r.question_id] = counts.get(r.question_id, 0) + 1
        return counts

    def _target_difficulty(self, learner_id: str, topic_id: str) -> str:
        """目标出题难度 = 掌握度映射难度 与 学员偏好难度 融合。

        掌握度决定「该学到多难」,学员偏好(LearnerProfile.preferred_difficulty)体现
        「想被怎样挑战」。二者取序数平均并四舍五入,让偏好把难度往其方向拉半档,而不是
        完全接管——已建立信心的学员选 easy 也不会永远停在 easy。
        未设偏好(空串/未知值)时退回纯掌握度行为,访客/未登录零回归。
        """
        with get_session(self._settings) as session:
            row = session.exec(
                select(Mastery).where(
                    Mastery.learner_id == learner_id, Mastery.topic_id == topic_id
                )
            ).first()
            profile = session.get(LearnerProfile, learner_id)
        level = row.level.value if row else MasteryLevel.UNKNOWN.value
        mastery_diff = _MASTERY_TO_DIFFICULTY.get(level, "easy")

        preferred = getattr(profile, "preferred_difficulty", "") if profile else ""
        if preferred not in _DIFFICULTY_ORDER:
            return mastery_diff
        blended = round((_DIFFICULTY_ORDER[mastery_diff] + _DIFFICULTY_ORDER[preferred]) / 2)
        return _ORDER_TO_DIFFICULTY.get(blended, mastery_diff)

    def select_question(
        self,
        learner_id: str,
        course_pack_id: str,
        weak_topics: list[str],
        retriever=None,
        exclude_ids: list[str] | None = None,
    ) -> dict:
        """挑一道待练题。

        exclude_ids:本轮已展示给学员、希望「换掉」的题(前端点「换一题」时回传)。
        选题会先跳过这些题;当某知识点的题被排除光了,就轮换到下一个知识点,
        让「换一题」真正换题而不是反复给同一道(修复缺陷)。领域无关不变。
        """
        excluded = set(exclude_ids or [])
        ordered = self._ordered_topics(weak_topics)
        if not ordered:
            return {}

        fallback: dict | None = None
        for topic_id in ordered:
            with get_session(self._settings) as session:
                rows = session.exec(
                    select(QuestionBank).where(
                        QuestionBank.course_pack_id == course_pack_id,
                        QuestionBank.topic_id == topic_id,
                    )
                ).all()

            # 候选池:预置/已审核题优先;无则退到任意已有题
            pool = [r for r in rows if r.approved_by] or list(rows)
            unseen = [r for r in pool if r.question_id not in excluded]
            if unseen:
                chosen = self._pick_from_pool(learner_id, topic_id, unseen)
                if chosen is not None:
                    return self._question_dict(chosen)
            # 该知识点全部被排除:先记一个兜底(所有题都练过时用),继续看下个知识点
            if fallback is None and pool:
                chosen = self._pick_from_pool(learner_id, topic_id, pool)
                if chosen is not None:
                    fallback = self._question_dict(chosen)

        # 所有知识点的现有题都被排除过 → LLM 依 RAG 生成新题(第一个知识点)
        primary = ordered[0]
        target = self._target_difficulty(learner_id, primary)
        generated = self._generate_question(course_pack_id, primary, retriever, target)
        if generated and generated.get("question_id") not in excluded:
            return generated
        # 生成题也重复(或无法生成)→ 回退到已排除池里的一道,保证一轮训练可跑通
        return fallback or generated

    def _question_dict(self, row) -> dict:
        return {
            "question_id": row.question_id,
            "topic_id": row.topic_id,
            "prompt": row.prompt,
            "reference_answer": row.reference_answer,
            "difficulty": row.difficulty,
            "source": row.source.value,
        }


    def _pick_from_pool(self, learner_id: str, topic_id: str, pool: list) -> object | None:
        """自适应 + 防重复选题。

        1) 目标难度按掌握度映射,取不到则按降级顺序放宽;
        2) 同难度内优先未做过的题;都做过则取作答次数最少的,按 question_id 稳定排序
           并用「已做题数」做偏移轮换,确定性地避免每次都命中同一题(利于测试复现)。
        """
        if not pool:
            return None
        target = self._target_difficulty(learner_id, topic_id)
        counts = self._recent_attempt_counts(learner_id, [q.question_id for q in pool])

        for difficulty in _DIFFICULTY_FALLBACK.get(target, [target]):
            bucket = [q for q in pool if (q.difficulty or "medium") == difficulty]
            if not bucket:
                continue
            bucket.sort(key=lambda q: (counts.get(q.question_id, 0), q.question_id))
            attempted_total = sum(1 for q in bucket if counts.get(q.question_id, 0) > 0)
            # 全部做过时用已做题数做偏移,轮换到下一道;否则天然取到未做过的首题
            return bucket[attempted_total % len(bucket)]
        return pool[0]

    def _generate_question(
        self, course_pack_id: str, topic_id: str, retriever, difficulty: str = "medium"
    ) -> dict:
        topic_name = self._topic_name(topic_id)
        course_id = self._topic_course(topic_id)
        course = self._pack.get_course(course_id)
        course_name = course.name if course else course_id
        corpus = ""
        if retriever is not None:
            # 用「课程名 + 知识点」锚定检索,避免泛化知识点名跑题到其它框架
            chunks = retriever.retrieve(
                course_pack_id=course_pack_id,
                query=f"{course_name} {topic_name}",
                course_ids=[course_id] if course_id else None,
                top_k=3,
            )
            corpus = "\n".join(c.get("text", "")[:400] for c in chunks)
        prompt_text = ""
        reference = ""
        try:
            raw = self._llm.complete(
                _GEN_TEMPLATE.format(
                    course_name=course_name,
                    topic_name=topic_name,
                    difficulty=difficulty,
                    corpus=corpus or "(无材料)",
                ),
                system=_GEN_SYSTEM,
            )
            parsed = _parse_llm_json(raw)
            prompt_text = str(parsed.get("prompt", "")).strip()
            reference = str(parsed.get("reference_answer", "")).strip()
        except Exception:
            prompt_text = ""
        if not prompt_text:
            # 兜底:用知识点名构造一道说明题,保证一轮训练可跑通
            prompt_text = f"请用自己的话解释「{topic_name}」的核心概念与作用。"
            reference = corpus[:200]

        qid = "q_" + hashlib.sha1(
            f"{course_pack_id}|{topic_id}|{prompt_text}".encode("utf-8")
        ).hexdigest()[:16]
        with get_session(self._settings) as session:
            if session.get(QuestionBank, qid) is None:
                session.add(
                    QuestionBank(
                        question_id=qid,
                        course_pack_id=course_pack_id,
                        topic_id=topic_id,
                        prompt=prompt_text[:500],
                        reference_answer=reference[:1000],
                        difficulty=difficulty,
                        source=QuestionSource.LLM_GENERATED,
                        approved_by="",  # 候选:待讲师审核沉淀
                    )
                )
                session.commit()
        return {
            "question_id": qid,
            "topic_id": topic_id,
            "prompt": prompt_text,
            "reference_answer": reference,
            "difficulty": difficulty,
            "source": QuestionSource.LLM_GENERATED.value,
        }

    # --- 批改 ---

    def get_question(self, course_pack_id: str, question_id: str) -> dict:
        """按 question_id 从题库重载完整题目(含参考答案,供批改服务端用)。

        批改端点不信任前端回传的题目,按 id 重载以防泄题/篡改;缺失返回 {}。
        """
        with get_session(self._settings) as session:
            row = session.get(QuestionBank, question_id)
        if row is None or row.course_pack_id != course_pack_id:
            return {}
        return {
            "question_id": row.question_id,
            "topic_id": row.topic_id,
            "prompt": row.prompt,
            "reference_answer": row.reference_answer,
            "difficulty": row.difficulty,
            "source": row.source.value,
        }

    # --- 讲师审核沉淀(ADR-0006 飞轮:candidate → approved) ---

    def list_candidate_questions(self, course_pack_id: str) -> list[dict]:
        """列出待审核候选题(LLM 生成、approved_by 为空)。

        供讲师端审核:含 reference_answer(讲师需看参考答案才能判断题目质量),
        故此方法仅经讲师守卫路由调用,不暴露给学生端。附知识点名便于阅读。
        """
        with get_session(self._settings) as session:
            rows = session.exec(
                select(QuestionBank)
                .where(
                    QuestionBank.course_pack_id == course_pack_id,
                    QuestionBank.source == QuestionSource.LLM_GENERATED,
                    QuestionBank.approved_by == "",
                )
                .order_by(QuestionBank.created_at)  # type: ignore[arg-type]
            ).all()
        return [
            {
                "question_id": r.question_id,
                "topic_id": r.topic_id,
                "topic_name": self._topic_name(r.topic_id),
                "prompt": r.prompt,
                "reference_answer": r.reference_answer,
                "difficulty": r.difficulty,
                "source": r.source.value,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]

    def approve_question(self, course_pack_id: str, question_id: str, approved_by: str) -> dict:
        """讲师通过候选题:写 approved_by,沉淀为优先出题来源。

        幂等:重复审核只覆盖 approved_by。题目不存在/跨课程包 → ValueError。
        approved_by 须非空(由认证讲师身份派生,防伪造)。
        """
        if not approved_by:
            raise ValueError("审核必须提供 approved_by")
        with get_session(self._settings) as session:
            row = session.get(QuestionBank, question_id)
            if row is None or row.course_pack_id != course_pack_id:
                raise ValueError(f"question_not_found: {question_id}")
            row.approved_by = approved_by
            session.add(row)
            session.commit()
            approved = {
                "question_id": row.question_id,
                "topic_id": row.topic_id,
                "approved_by": row.approved_by,
            }
        return approved

    def reject_question(self, course_pack_id: str, question_id: str) -> dict:
        """讲师驳回候选题:删除该候选。

        只删仍待审核的 LLM 候选(approved_by 为空),避免误删已沉淀/预置题;
        题目不存在/跨课程包 → ValueError。
        """
        with get_session(self._settings) as session:
            row = session.get(QuestionBank, question_id)
            if row is None or row.course_pack_id != course_pack_id:
                raise ValueError(f"question_not_found: {question_id}")
            if row.approved_by:
                raise ValueError("只能驳回待审核候选题(已沉淀题不可驳回)")
            session.delete(row)
            session.commit()
        return {"question_id": question_id, "rejected": True}

    def grade(self, question: dict, learner_answer: str) -> dict:
        topic_id = question.get("topic_id", "")
        dimensions = self._rubric_dimensions_for(topic_id)
        answer = (learner_answer or "").strip()
        if not answer:
            return {
                "score": 0.0,
                "passed": False,
                "feedback": "未作答,无法评分。请给出你的解答。",
                "dimensions": [{**d, "score": 0.0} for d in dimensions],
            }

        dim_desc = "; ".join(f"{d['key']}({d['name']})" for d in dimensions) or "综合"
        scored: list[dict] | None = None
        feedback = ""
        try:
            raw = self._llm.complete(
                _GRADE_TEMPLATE.format(
                    prompt=question.get("prompt", ""),
                    reference=question.get("reference_answer", "") or "(无参考答案)",
                    dimensions=dim_desc,
                    answer=answer,
                ),
                system=_GRADE_SYSTEM,
            )
            parsed = _parse_llm_json(raw)
            raw_dims = parsed.get("dimensions")
            if isinstance(raw_dims, list) and raw_dims:
                by_key = {}
                for item in raw_dims:
                    if isinstance(item, dict) and item.get("key") is not None:
                        try:
                            by_key[str(item["key"])] = max(0.0, min(1.0, float(item.get("score", 0))))
                        except (TypeError, ValueError):
                            continue
                if by_key:
                    scored = [{**d, "score": by_key.get(d["key"], 0.0)} for d in dimensions]
            feedback = str(parsed.get("feedback", "")).strip()
        except Exception:
            scored = None

        if scored is None:
            # 启发式回退:与参考答案的 token 重合度作为单一得分
            ref_tokens = _tokenize(question.get("reference_answer", ""))
            ans_tokens = _tokenize(answer)
            overlap = len(ref_tokens & ans_tokens) / len(ref_tokens) if ref_tokens else (
                1.0 if len(ans_tokens) >= 8 else 0.5
            )
            overlap = round(max(0.0, min(1.0, overlap)), 4)
            scored = [{**d, "score": overlap} for d in dimensions]
            if not feedback:
                feedback = "已按参考答案要点比对给出评分,可对照参考答案补全遗漏要点。"

        total_w = sum(d.get("weight", 1.0) for d in scored) or 1.0
        score = round(sum(d["score"] * d.get("weight", 1.0) for d in scored) / total_w, 4)
        return {
            "score": score,
            "passed": score >= KNOWN_SCORE_THRESHOLD,
            "feedback": feedback or "评分完成。",
            "dimensions": scored,
        }

    # --- 更新掌握度 ---

    def update_mastery(self, learner_id: str, question: dict, grade: dict) -> dict:
        topic_id = question.get("topic_id", "")
        score = float(grade.get("score", 0.0))
        if score >= KNOWN_SCORE_THRESHOLD:
            new_level = MasteryLevel.KNOWN
        elif score >= FUZZY_SCORE_THRESHOLD:
            new_level = MasteryLevel.FUZZY
        else:
            new_level = MasteryLevel.UNKNOWN

        overwritten = False
        with get_session(self._settings) as session:
            if session.get(Learner, learner_id) is None:
                session.add(Learner(learner_id=learner_id))

            session.add(
                ExerciseAttempt(
                    learner_id=learner_id,
                    question_id=question.get("question_id", ""),
                    topic_id=topic_id,
                    score=score,
                    feedback=grade.get("feedback", "")[:500],
                )
            )

            existing = session.exec(
                select(Mastery).where(
                    Mastery.learner_id == learner_id, Mastery.topic_id == topic_id
                )
            ).first()
            if existing is None:
                session.add(
                    Mastery(
                        learner_id=learner_id,
                        topic_id=topic_id,
                        level=new_level,
                        source=MasterySource.SYSTEM_INFERRED,
                    )
                )
            elif existing.source == MasterySource.INSTRUCTOR_CORRECTED:
                # 讲师修正优先,系统批改不覆盖
                pass
            else:
                existing.level = new_level
                overwritten = True
                session.add(existing)
            session.commit()

        return {
            "topic_id": topic_id,
            "level": new_level.value,
            "score": score,
            "overwritten": overwritten,
        }
