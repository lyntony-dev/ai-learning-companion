"""横切装饰:C 个性化 & D 主动建议 (ADR-0004 / DESIGN §4.2)。

不单独成图,作为主图进入/退出边界的节点挂载:
  - C 个性化:进入前把学员掌握度画像/薄弱点注入 State,供问答子图 answer/retrieve 使用。
  - D 主动建议:进入前生成会话开场 opener,退出前生成收尾建议。

画像来源为可注入的 provider(默认空画像),避免引擎耦合具体持久化实现。
"""

from __future__ import annotations

from typing import Callable, Protocol

from app.engine.orchestration.state import TutorState, append_trace, new_trace_event


class MasteryProvider(Protocol):
    """C 装饰所需的最小读面。SqlLearnerModel / EmptyLearnerModel 均满足。"""

    def profile(self, learner_id: str, course_pack_id: str) -> dict: ...

    def weak_topics(self, learner_id: str, course_pack_id: str) -> list[str]: ...

    def learner_profile(self, learner_id: str) -> dict: ...


def make_personalization_opener(provider: MasteryProvider) -> Callable[[TutorState], dict]:
    """C + D 进入装饰:注入画像 + 生成开场。"""

    def enter(state: TutorState) -> dict:
        learner = state.get("learner_id", "")
        pack = state.get("course_pack_id", "")
        profile = provider.profile(learner, pack)
        weak = provider.weak_topics(learner, pack)
        # C:学员自述画像(背景/目标/偏好难度),供答复装饰调深浅;新学员/占位为空 dict
        get_lp = getattr(provider, "learner_profile", None)
        learner_prof = get_lp(learner) if callable(get_lp) else {}
        opener = (
            f"欢迎回来!我们上次在这些薄弱点上还可以加强:{', '.join(weak)}。"
            if weak
            else "你好!我可以基于课程材料回答问题,随时开始。"
        )
        return {
            "mastery_profile": profile,
            "weak_topics": weak,
            "learner_profile": learner_prof,
            "session_opener": opener,
            "trace": append_trace(
                state,
                new_trace_event(
                    "personalize_opener",
                    output_summary=f"weak={len(weak)} profile={'y' if learner_prof else 'n'}",
                ),
            ),
        }

    return enter


def closing_advice(state: TutorState) -> dict:
    """D 退出装饰:基于本轮结果给收尾建议。"""
    if state.get("refused"):
        suggestion = "这次没找到足够材料,建议补充相关课件后再试,或换个更具体的问法。"
    elif state.get("evidence_level") == "weak":
        suggestion = "本题材料证据有限,建议结合课件原文再确认关键结论。"
    else:
        weak = state.get("weak_topics") or []
        suggestion = (
            f"下一步可以练习这些薄弱点:{', '.join(weak)}。" if weak else "继续保持,可以尝试更进阶的问题。"
        )
    return {
        "closing_suggestion": suggestion,
        "trace": append_trace(state, new_trace_event("closing_advice", output_summary="ok")),
    }
