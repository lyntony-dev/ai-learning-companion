"""AI 提取候选 taxonomy / 题库 (ADR-0006 / DESIGN §6)。

从已解析的课程资料出发,用 LLM 生成**候选**知识点与练习题。
产物一律标记 status=candidate,须经讲师审核后才 approved(ADR-0006)。

设计要点:
  - 引擎不硬编码任何课程内容:提取输入全部来自 MaterialDoc。
  - LLM 可切换(mock / openai_compatible),mock 走确定性启发式,保证离线跑通。
  - MVP 覆盖单一垂类切片够用的最小提取;更强的结构化抽取为扩展点。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.course_pack.schema import ArtifactStatus
from app.ingestion.pack_parsers import MaterialDoc
from app.llm import LLMClient, get_llm_client

# LLM 提取提示词。要求严格 JSON,便于解析;失败可回退启发式。
_EXTRACT_SYSTEM = (
    "你是课程内容结构化助手。基于给定课程资料,抽取候选知识点与练习题。"
    "只输出 JSON,不要多余文字。"
)

_EXTRACT_TEMPLATE = """课程: {course_id}
资料片段(可能截断):
{corpus}

请输出如下 JSON:
{{
  "topics": [{{"name": "知识点名(简短)", "summary": "一句话说明"}}],
  "questions": [{{"prompt": "题干", "topic_name": "关联知识点名", "difficulty": "easy|medium|hard"}}]
}}
最多 {max_topics} 个知识点、{max_questions} 道题。"""


@dataclass
class CandidateTopic:
    name: str
    course_id: str
    summary: str = ""
    status: str = ArtifactStatus.CANDIDATE.value


@dataclass
class CandidateQuestion:
    prompt: str
    course_id: str
    topic_name: str = ""
    difficulty: str = "medium"
    status: str = ArtifactStatus.CANDIDATE.value


@dataclass
class ExtractionResult:
    course_pack_id: str
    topics: list[CandidateTopic] = field(default_factory=list)
    questions: list[CandidateQuestion] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "course_pack_id": self.course_pack_id,
            "topics": [t.__dict__ for t in self.topics],
            "questions": [q.__dict__ for q in self.questions],
        }


def _build_corpus(docs: list[MaterialDoc], max_chars: int) -> str:
    """把某课资料拼成一段供 LLM 阅读的语料(截断)。"""
    parts: list[str] = []
    total = 0
    for d in docs:
        seg = d.text.strip()
        if not seg:
            continue
        parts.append(seg)
        total += len(seg)
        if total >= max_chars:
            break
    return "\n\n".join(parts)[:max_chars]


def _parse_llm_json(raw: str) -> dict:
    """从 LLM 返回中稳健抽取 JSON(容忍 ```json 包裹与前后噪声)。"""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}


def _heuristic_topics(docs: list[MaterialDoc], course_id: str, limit: int) -> list[CandidateTopic]:
    """LLM 不可用/解析失败时的启发式回退:用 section 名做候选知识点。"""
    seen: dict[str, CandidateTopic] = {}
    for d in docs:
        name = (d.section or d.source_path).strip()
        if not name or name in seen:
            continue
        seen[name] = CandidateTopic(
            name=name[:60],
            course_id=course_id,
            summary=d.text.strip().replace("\n", " ")[:80],
        )
        if len(seen) >= limit:
            break
    return list(seen.values())


def extract_candidates(
    course_pack_id: str,
    docs: list[MaterialDoc],
    llm: LLMClient | None = None,
    max_topics_per_course: int = 6,
    max_questions_per_course: int = 4,
    corpus_chars: int = 4000,
) -> ExtractionResult:
    """按课程分组,用 LLM 提取候选知识点/题目(带启发式回退)。"""
    llm = llm or get_llm_client()
    result = ExtractionResult(course_pack_id=course_pack_id)

    by_course: dict[str, list[MaterialDoc]] = {}
    for d in docs:
        by_course.setdefault(d.course_id, []).append(d)

    for course_id, cdocs in by_course.items():
        corpus = _build_corpus(cdocs, corpus_chars)
        if not corpus:
            continue
        prompt = _EXTRACT_TEMPLATE.format(
            course_id=course_id,
            corpus=corpus,
            max_topics=max_topics_per_course,
            max_questions=max_questions_per_course,
        )
        parsed: dict = {}
        try:
            raw = llm.complete(prompt, system=_EXTRACT_SYSTEM)
            parsed = _parse_llm_json(raw)
        except Exception:
            parsed = {}

        topics = parsed.get("topics") if isinstance(parsed, dict) else None
        if topics:
            for t in topics[:max_topics_per_course]:
                name = str(t.get("name", "")).strip()
                if not name:
                    continue
                result.topics.append(
                    CandidateTopic(
                        name=name[:60],
                        course_id=course_id,
                        summary=str(t.get("summary", ""))[:200],
                    )
                )
        else:
            # 回退:section 启发式
            result.topics.extend(
                _heuristic_topics(cdocs, course_id, max_topics_per_course)
            )

        questions = parsed.get("questions") if isinstance(parsed, dict) else None
        if questions:
            for q in questions[:max_questions_per_course]:
                prompt_text = str(q.get("prompt", "")).strip()
                if not prompt_text:
                    continue
                result.questions.append(
                    CandidateQuestion(
                        prompt=prompt_text[:500],
                        course_id=course_id,
                        topic_name=str(q.get("topic_name", ""))[:60],
                        difficulty=str(q.get("difficulty", "medium")),
                    )
                )

    return result
