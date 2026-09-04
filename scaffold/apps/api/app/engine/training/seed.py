"""预置题库入库 (E) (ADR-0006:课程包=题库领域源;讲师可编写)。

把 CoursePack.questions(加载自 course_pack/<id>/questions/*.yaml)幂等 upsert
进业务库 QuestionBank(source=PRESET, approved_by="course_pack")。

设计约束:
  - 幂等:重复调用不产生重复行,只在缺失时插入。
  - 非破坏:只处理预置题,绝不触碰 LLM_GENERATED 候选(审核飞轮的产物)。
  - question_id 与 service._generate_question 的哈希配方一致,使同题的 LLM
    候选与预置题落到同一 id,便于收敛/去重。
"""

from __future__ import annotations

import hashlib

from app.course_pack.schema import CoursePack
from app.persistence import QuestionBank, QuestionSource, get_session


def preset_question_id(course_pack_id: str, topic_id: str, prompt: str, slug: str = "") -> str:
    """预置题 id:有 slug 用可读 id,否则按 (pack|topic|prompt) 哈希。

    哈希分支与 SqlTrainingService._generate_question 的配方一致,保证同一题的
    LLM 生成候选与预置题会收敛到同一 question_id。
    """
    slug = (slug or "").strip()
    if slug:
        return f"q_preset_{course_pack_id}_{slug}"
    return "q_" + hashlib.sha1(
        f"{course_pack_id}|{topic_id}|{prompt}".encode("utf-8")
    ).hexdigest()[:16]


def seed_question_bank(pack: CoursePack, settings=None) -> int:
    """把课程包预置题幂等 upsert 进 QuestionBank。返回新插入的题目数。

    - 已存在(同 id)则跳过,不覆盖(避免抹掉运行期审核状态)。
    - 只写 source=PRESET;不读取/修改任何 LLM_GENERATED 行。
    """
    questions = pack.questions.questions
    if not questions:
        return 0
    inserted = 0
    with get_session(settings) as session:
        for q in questions:
            qid = preset_question_id(pack.course_pack_id, q.topic_id, q.prompt, q.id)
            if session.get(QuestionBank, qid) is not None:
                continue
            session.add(
                QuestionBank(
                    question_id=qid,
                    course_pack_id=pack.course_pack_id,
                    topic_id=q.topic_id,
                    prompt=q.prompt[:500],
                    reference_answer=q.reference_answer[:1000],
                    difficulty=q.difficulty.value,
                    source=QuestionSource.PRESET,
                    approved_by="course_pack",  # 预置=课程包已沉淀,选题优先
                )
            )
            inserted += 1
        if inserted:
            session.commit()
    return inserted
