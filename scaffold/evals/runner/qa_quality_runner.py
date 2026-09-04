"""问答质量 eval 运行器 (feat-010 / DESIGN §9)。

离线可复现地校验两条硬质量线(不依赖真实 Ark):
  - 拒答:证据不足时 refused=True 且不产出引用(不编造页码)。
  - 引用正确性:有证据时 refused=False,answer 带 [n],且每条 citation
    的 chunk_id 都能在本轮检索结果里找到(引用对齐真实来源)。

数据集:scaffold/evals/datasets/qa_quality.json。
用法:
  cd scaffold/apps/api && .venv/bin/python ../../evals/runner/qa_quality_runner.py
被 tests/test_evals_qa_quality.py 复用做门禁。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.engine.orchestration.main_graph import build_main_graph, initial_state

DATASET = (
    Path(__file__).resolve().parents[1] / "datasets" / "qa_quality.json"
)

# 证据档位 → 检索打分(对齐 qa_graph 阈值:STRONG>=0.75,insufficient<0.35)
_EVIDENCE_SCORE = {"strong": 0.9, "weak": 0.5, "insufficient": 0.05}


class _EvalRetriever:
    """按 case 的证据档位返回确定性打分 chunk。"""

    def __init__(self, score: float) -> None:
        self._score = score

    def retrieve(self, course_pack_id, query, course_ids=None, top_k=5):
        return [
            {
                "chunk_id": "eval_chunk_1",
                "text": "LangGraph State 在节点间共享上下文;条件边按状态决定分支。",
                "score": self._score,
                "metadata": {
                    "course_id": "langgraph_multiagent",
                    "section": "StateGraph",
                    "source_path": "slides/s.html",
                    "slide_no": 6,
                },
            }
        ]


class _EvalLLM:
    """确定性回答:始终带 [1] 引用(引用正确性由检索对齐校验,而非文本)。"""

    def complete(self, prompt, system=None, **kwargs):
        return "根据课程材料,State 用于在节点之间共享上下文 [1]。"


@dataclass
class CaseResult:
    case_id: str
    passed: bool
    reasons: list[str] = field(default_factory=list)


def _check_case(case: dict) -> CaseResult:
    evidence = case.get("evidence", "strong")
    retriever = _EvalRetriever(_EVIDENCE_SCORE.get(evidence, 0.9))
    graph = build_main_graph(retriever, llm=_EvalLLM())
    out = graph.invoke(
        initial_state(
            case.get("query", ""),
            "ai_agent",
            task_type=case.get("task_type", "rag_answer"),
            max_retry=1,
        )
    )
    expect = case.get("expect", {})
    reasons: list[str] = []

    refused = bool(out.get("refused"))
    citations = out.get("citations", []) or []
    answer = out.get("answer", "")
    chunk_ids = {c.get("chunk_id") for c in retriever.retrieve("", "")}

    if "refused" in expect and refused != expect["refused"]:
        reasons.append(f"refused 期望 {expect['refused']} 实际 {refused}")
    if "min_citations" in expect and len(citations) < expect["min_citations"]:
        reasons.append(f"citations {len(citations)} < min {expect['min_citations']}")
    if "max_citations" in expect and len(citations) > expect["max_citations"]:
        reasons.append(f"citations {len(citations)} > max {expect['max_citations']}")
    if "answer_contains" in expect and expect["answer_contains"] not in answer:
        reasons.append(f"answer 不含 {expect['answer_contains']!r}")
    # 引用对齐:每条 citation 的 chunk_id 必须来自本轮检索
    for c in citations:
        if c.get("chunk_id") not in chunk_ids:
            reasons.append(f"citation chunk_id {c.get('chunk_id')!r} 不在检索来源中")

    return CaseResult(case_id=case.get("id", "?"), passed=not reasons, reasons=reasons)


def run(dataset_path: Path = DATASET) -> list[CaseResult]:
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    return [_check_case(c) for c in data.get("cases", [])]


def main() -> int:
    results = run()
    passed = sum(1 for r in results if r.passed)
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        detail = "" if r.passed else f" — {'; '.join(r.reasons)}"
        print(f"[{mark}] {r.case_id}{detail}")
    print(f"\n{passed}/{len(results)} cases passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
