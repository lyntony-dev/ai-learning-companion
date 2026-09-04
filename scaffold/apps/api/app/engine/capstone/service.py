"""结课项目立项 + 个性化清单服务 (F) (DESIGN §4 / ADR-0005)。

重设计后的项目陪练:不再让学生写自述让 LLM 判定(空壳),而是——
  1. 学生立项(goal/audience/difficulty:想做什么 Agent、面向谁、预期难点);
  2. 引擎基于课程包 + RAG 证据,用 LLM 把想法收敛成「项目卡」(title/scope/tech_stack),
     并为每个里程碑生成「针对这个项目的、可勾选的具体清单」——把"满足需要"的标准
     绑定到学生自己的项目上;
  3. 学生按清单勾选推进,里程碑状态从勾选完成度派生(全勾→passed / 部分→in_progress),
     写回 milestone_progress 供教学洞察(T)聚合。

领域无关:里程碑序列/名称/交付要求均来自注入的 CoursePack,技术选型由 LLM 依课程包内容
推断,不在引擎里硬编码任何具体课程/项目/技术。
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Protocol

from sqlmodel import select

from app.course_pack.schema import CoursePack
from app.engine.retrieval import Retriever
from app.llm import LLMClient, get_llm_client
from app.persistence import (
    CapstoneProject,
    Learner,
    MilestoneProgress,
    MilestoneStatus,
    get_session,
)

# 每个里程碑清单项数量上下限(生成/回退都遵守)
_MIN_ITEMS_PER_MILESTONE = 2
_MAX_ITEMS_PER_MILESTONE = 4

_PLAN_SYSTEM = (
    "你是结课项目的立项导师。学员给出他想做的 Agent 项目想法,你要基于课程涵盖的能力,"
    "把它收敛成一个清晰、可落地的项目计划,并为每个里程碑列出针对这个项目的、可勾选的具体任务。"
    "任务必须具体到这个项目(而不是通用套话),让学员一看就知道该做什么、做到什么算完成。"
    "只输出 JSON,不要多余文字。"
)


class CapstoneService(Protocol):
    """立项 + 个性化清单读写面(可注入替身)。"""

    def get_project(self, learner_id: str, course_pack_id: str) -> dict: ...

    def create_project(
        self,
        learner_id: str,
        course_pack_id: str,
        goal: str,
        audience: str,
        difficulty: str = "",
        retriever: Retriever | None = None,
    ) -> dict: ...

    def toggle_item(
        self, learner_id: str, course_pack_id: str, item_id: str, checked: bool
    ) -> dict: ...


def _parse_llm_json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {}
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else {}
    except json.JSONDecodeError:
        return {}


def _item_id(milestone_id: str, index: int, text: str) -> str:
    """稳定 item_id:同一里程碑内按序号+文本 sha1,便于前端勾选定位与幂等。"""
    digest = hashlib.sha1(f"{milestone_id}:{index}:{text}".encode()).hexdigest()[:8]
    return f"{milestone_id}-{digest}"


class SqlCapstoneService:
    """SQLModel 业务库实现。持有 CoursePack(capstone 里程碑序列)与 LLM。"""

    def __init__(self, course_pack: CoursePack, llm: LLMClient | None = None, settings=None) -> None:
        self._pack = course_pack
        self._llm = llm or get_llm_client(settings)
        self._settings = settings

    # --- 内部工具 ---

    def _milestones(self):
        return self._pack.capstone.milestones if self._pack.capstone else []

    def _capstone_meta(self) -> dict:
        c = self._pack.capstone
        return {
            "overview": c.overview if c else "",
            "background": c.background if c else "",
            "final_deliverable": c.final_deliverable if c else "",
        }

    def _load_row(self, learner_id: str, course_pack_id: str) -> CapstoneProject | None:
        with get_session(self._settings) as session:
            return session.exec(
                select(CapstoneProject).where(
                    CapstoneProject.learner_id == learner_id,
                    CapstoneProject.course_pack_id == course_pack_id,
                )
            ).first()

    def _milestone_statuses(
        self, learner_id: str, course_pack_id: str
    ) -> dict[str, MilestoneStatus]:
        with get_session(self._settings) as session:
            rows = session.exec(
                select(MilestoneProgress).where(
                    MilestoneProgress.learner_id == learner_id,
                    MilestoneProgress.course_pack_id == course_pack_id,
                )
            ).all()
        return {r.milestone: r.status for r in rows}

    # --- 读:项目状态(无项目则返回向导所需的作业说明)---

    def get_project(self, learner_id: str, course_pack_id: str) -> dict:
        row = self._load_row(learner_id, course_pack_id)
        if row is None:
            return self._response(learner_id, course_pack_id, None)
        return self._response(learner_id, course_pack_id, row)

    def _response(
        self, learner_id: str, course_pack_id: str, row: CapstoneProject | None
    ) -> dict:
        meta = self._capstone_meta()
        capstone_name = self._pack.capstone.name if self._pack.capstone else course_pack_id
        base = {
            "course_pack_id": course_pack_id,
            "capstone_name": capstone_name,
            "has_project": row is not None,
            "card": None,
            "milestones": [],
            "current_milestone_id": "",
            "passed_count": 0,
            "total": len(self._milestones()),
            "all_passed": False,
            **meta,
        }
        if row is None:
            # 无项目:向导态,里程碑仅给出作业说明(name/deliverable/hint),无清单/无状态
            base["milestones"] = [
                {
                    "milestone_id": m.id,
                    "name": m.name,
                    "status": MilestoneStatus.NOT_STARTED.value,
                    "deliverable": m.deliverable,
                    "hint": m.hint,
                    "items": [],
                }
                for m in self._milestones()
            ]
            return base

        card = _parse_llm_json(row.card_json) if row.card_json else {}
        checklist = _parse_llm_json(row.checklist_json) if row.checklist_json else {}
        statuses = self._milestone_statuses(learner_id, course_pack_id)
        milestones = []
        passed = 0
        current = ""
        for m in self._milestones():
            items = checklist.get(m.id, [])
            status = statuses.get(m.id, MilestoneStatus.NOT_STARTED).value
            if status == MilestoneStatus.PASSED.value:
                passed += 1
            elif not current:
                current = m.id
            milestones.append(
                {
                    "milestone_id": m.id,
                    "name": m.name,
                    "status": status,
                    "deliverable": m.deliverable,
                    "hint": m.hint,
                    "items": items,
                }
            )
        base["card"] = {
            "title": str(card.get("title", "")),
            "scope": str(card.get("scope", "")),
            "tech_stack": [str(t) for t in card.get("tech_stack", []) if str(t).strip()],
        }
        base["milestones"] = milestones
        base["passed_count"] = passed
        base["current_milestone_id"] = current
        base["all_passed"] = bool(milestones) and passed == len(milestones)
        return base

    # --- 写:立项(生成项目卡 + 个性化清单)---

    def create_project(
        self,
        learner_id: str,
        course_pack_id: str,
        goal: str,
        audience: str,
        difficulty: str = "",
        retriever: Retriever | None = None,
    ) -> dict:
        goal = (goal or "").strip()
        audience = (audience or "").strip()
        difficulty = (difficulty or "").strip()

        card, checklist = self._generate_plan(course_pack_id, goal, audience, difficulty, retriever)

        with get_session(self._settings) as session:
            if session.get(Learner, learner_id) is None:
                session.add(Learner(learner_id=learner_id))
            row = session.exec(
                select(CapstoneProject).where(
                    CapstoneProject.learner_id == learner_id,
                    CapstoneProject.course_pack_id == course_pack_id,
                )
            ).first()
            if row is None:
                row = CapstoneProject(
                    learner_id=learner_id,
                    course_pack_id=course_pack_id,
                )
            row.goal = goal
            row.audience = audience
            row.difficulty = difficulty
            row.card_json = json.dumps(card, ensure_ascii=False)
            row.checklist_json = json.dumps(checklist, ensure_ascii=False)
            session.add(row)
            # 重新立项:里程碑状态全部重置为 not_started
            for m in self._milestones():
                mp = session.exec(
                    select(MilestoneProgress).where(
                        MilestoneProgress.learner_id == learner_id,
                        MilestoneProgress.course_pack_id == course_pack_id,
                        MilestoneProgress.milestone == m.id,
                    )
                ).first()
                if mp is None:
                    mp = MilestoneProgress(
                        learner_id=learner_id,
                        course_pack_id=course_pack_id,
                        milestone=m.id,
                        status=MilestoneStatus.NOT_STARTED,
                    )
                else:
                    mp.status = MilestoneStatus.NOT_STARTED
                session.add(mp)
            session.commit()

        return self.get_project(learner_id, course_pack_id)

    def _generate_plan(
        self,
        course_pack_id: str,
        goal: str,
        audience: str,
        difficulty: str,
        retriever: Retriever | None,
    ) -> tuple[dict, dict]:
        """LLM + RAG 生成项目卡与每里程碑清单;解析失败回退到基于 deliverable 的保底清单。"""
        milestones = self._milestones()
        meta = self._capstone_meta()

        # RAG 证据:用立项想法锚定课程材料,让技术选型/任务贴合课程涵盖的能力
        evidence = ""
        if retriever is not None and goal:
            try:
                hits = retriever.retrieve(course_pack_id, f"{goal} {audience}", top_k=4)
                evidence = "\n".join(h.get("text", "")[:400] for h in hits)[:2000]
            except Exception:
                evidence = ""

        milestone_lines = "\n".join(
            f"- {m.id} / {m.name}:{m.deliverable}" for m in milestones
        )
        prompt = self._plan_prompt(goal, audience, difficulty, meta, milestone_lines, evidence)

        parsed: dict = {}
        try:
            raw = self._llm.complete(prompt, system=_PLAN_SYSTEM)
            parsed = _parse_llm_json(raw)
        except Exception:
            logging.getLogger(__name__).warning(
                "capstone plan LLM generation failed, falling back to deliverable-split checklist",
                exc_info=True,
            )
            parsed = {}

        card = self._extract_card(parsed, goal)
        checklist = self._extract_checklist(parsed, milestones)
        return card, checklist

    def _plan_prompt(
        self,
        goal: str,
        audience: str,
        difficulty: str,
        meta: dict,
        milestone_lines: str,
        evidence: str,
    ) -> str:
        ms_ids = [m.id for m in self._milestones()]
        return f"""课程结课项目总体要求:
{meta['overview']}
最终交付物:{meta['final_deliverable']}

学员立项想法:
- 想做的 Agent:{goal}
- 面向谁/什么场景:{audience}
- 预期难点:{difficulty or "(未填)"}

课程材料摘录(用于锚定技术选型,仅供参考):
{evidence or "(无)"}

结课里程碑(id / 名称:交付要求):
{milestone_lines}

请基于以上,为这个学员的项目输出 JSON:
{{
  "title": "收敛后的项目名(一句话)",
  "scope": "2-3 句说明这个项目具体做什么、范围边界",
  "tech_stack": ["基于课程能力推荐的关键技术选型, 3-5 项"],
  "milestones": [
    {{"milestone_id": "里程碑id(必须来自: {ms_ids})",
      "items": ["针对本项目的具体可勾选任务, {_MIN_ITEMS_PER_MILESTONE}-{_MAX_ITEMS_PER_MILESTONE} 条"]}}
  ]
}}
要求:每个里程碑都要出现;items 要具体到这个项目(提到项目的场景/数据/工具),不要通用套话。"""

    def _extract_card(self, parsed: dict, goal: str) -> dict:
        title = str(parsed.get("title", "")).strip() or (goal[:40] if goal else "我的 Agent 项目")
        scope = str(parsed.get("scope", "")).strip() or goal
        tech = [str(t).strip() for t in parsed.get("tech_stack", []) if str(t).strip()]
        return {"title": title, "scope": scope, "tech_stack": tech[:6]}

    def _extract_checklist(self, parsed: dict, milestones) -> dict:
        """从 LLM 输出提取每里程碑清单;缺失/为空的里程碑用 deliverable 生成保底项。"""
        by_id: dict[str, list[str]] = {}
        for entry in parsed.get("milestones", []) or []:
            if not isinstance(entry, dict):
                continue
            mid = str(entry.get("milestone_id", "")).strip()
            items = [str(x).strip() for x in entry.get("items", []) if str(x).strip()]
            if mid and items:
                by_id[mid] = items[:_MAX_ITEMS_PER_MILESTONE]

        checklist: dict[str, list[dict]] = {}
        for m in milestones:
            texts = by_id.get(m.id) or self._fallback_items(m)
            checklist[m.id] = [
                {"id": _item_id(m.id, i, t), "text": t, "checked": False}
                for i, t in enumerate(texts)
            ]
        return checklist

    def _fallback_items(self, milestone) -> list[str]:
        """LLM 不可用/未覆盖某里程碑时的保底清单:拆解 deliverable 为可勾选项。"""
        deliverable = (milestone.deliverable or "").strip()
        # 按中文/英文句末标点切句,取非空句作为清单项
        parts = [p.strip() for p in re.split(r"[。;;\n]", deliverable) if p.strip()]
        if not parts:
            parts = [f"完成「{milestone.name}」的交付内容"]
        items = parts[:_MAX_ITEMS_PER_MILESTONE]
        if len(items) < _MIN_ITEMS_PER_MILESTONE:
            items.append(f"整理并说明「{milestone.name}」的产出")
        return items

    # --- 写:勾选清单项(派生里程碑状态)---

    def toggle_item(
        self, learner_id: str, course_pack_id: str, item_id: str, checked: bool
    ) -> dict:
        row = self._load_row(learner_id, course_pack_id)
        if row is None:
            raise ValueError("project_not_found")

        checklist = _parse_llm_json(row.checklist_json) if row.checklist_json else {}
        found_milestone = None
        for mid, items in checklist.items():
            for it in items:
                if it.get("id") == item_id:
                    it["checked"] = bool(checked)
                    found_milestone = mid
                    break
            if found_milestone:
                break
        if found_milestone is None:
            raise ValueError("item_not_found")

        with get_session(self._settings) as session:
            db_row = session.exec(
                select(CapstoneProject).where(
                    CapstoneProject.learner_id == learner_id,
                    CapstoneProject.course_pack_id == course_pack_id,
                )
            ).first()
            db_row.checklist_json = json.dumps(checklist, ensure_ascii=False)
            session.add(db_row)
            # 派生该里程碑状态:全勾→passed / 有勾→in_progress / 无勾→not_started
            items = checklist.get(found_milestone, [])
            new_status = self._derive_status(items)
            mp = session.exec(
                select(MilestoneProgress).where(
                    MilestoneProgress.learner_id == learner_id,
                    MilestoneProgress.course_pack_id == course_pack_id,
                    MilestoneProgress.milestone == found_milestone,
                )
            ).first()
            if mp is None:
                mp = MilestoneProgress(
                    learner_id=learner_id,
                    course_pack_id=course_pack_id,
                    milestone=found_milestone,
                    status=new_status,
                )
            else:
                mp.status = new_status
            session.add(mp)
            session.commit()

        return self.get_project(learner_id, course_pack_id)

    @staticmethod
    def _derive_status(items: list[dict]) -> MilestoneStatus:
        if not items:
            return MilestoneStatus.NOT_STARTED
        checked = sum(1 for it in items if it.get("checked"))
        if checked == 0:
            return MilestoneStatus.NOT_STARTED
        if checked == len(items):
            return MilestoneStatus.PASSED
        return MilestoneStatus.IN_PROGRESS
