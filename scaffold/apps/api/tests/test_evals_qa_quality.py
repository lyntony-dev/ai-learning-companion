"""feat-010 eval 门禁:问答拒答与引用正确性 (DESIGN §9)。

复用 scaffold/evals/runner/qa_quality_runner.py,把 eval 数据集当作门禁跑,
确保:证据不足→拒答不编造;有证据→带 [n] 且 citation 对齐真实检索来源。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNNER = REPO_ROOT / "scaffold" / "evals" / "runner" / "qa_quality_runner.py"

pytestmark = pytest.mark.skipif(not RUNNER.exists(), reason="eval runner 不存在")


def _load_runner():
    spec = importlib.util.spec_from_file_location("qa_quality_runner", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    # 注册到 sys.modules,@dataclass 需按 __module__ 解析注解
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_qa_quality_eval_all_pass() -> None:
    runner = _load_runner()
    results = runner.run()
    assert results, "eval 数据集为空"
    failures = [f"{r.case_id}: {'; '.join(r.reasons)}" for r in results if not r.passed]
    assert not failures, "eval 未全过:\n" + "\n".join(failures)
