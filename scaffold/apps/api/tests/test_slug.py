"""slug 生成单测 (CoursewareDoc v1)。前端 src/lib/slug.ts 须与此行为对齐。"""

from __future__ import annotations

from app.course_pack.slug import extract_explicit_anchor, heading_anchor, slugify


def test_slugify_basic_ascii() -> None:
    assert slugify("What You Learn") == "what-you-learn"


def test_slugify_chinese_preserved() -> None:
    assert slugify("这个项目学什么") == "这个项目学什么"


def test_slugify_mixed_and_punctuation() -> None:
    assert slugify("3.1 LLM 是什么?") == "3-1-llm-是什么"


def test_slugify_collapses_and_trims_dashes() -> None:
    assert slugify("  --Hello___World--  ") == "hello-world"


def test_extract_explicit_anchor() -> None:
    clean, anchor = extract_explicit_anchor("核心概念 {#core-concepts}")
    assert clean == "核心概念"
    assert anchor == "core-concepts"


def test_extract_explicit_anchor_absent() -> None:
    clean, anchor = extract_explicit_anchor("核心概念")
    assert clean == "核心概念"
    assert anchor is None


def test_heading_anchor_prefers_explicit() -> None:
    assert heading_anchor("介绍 {#intro}") == ("介绍", "intro")


def test_heading_anchor_falls_back_to_slug() -> None:
    assert heading_anchor("Getting Started") == ("Getting Started", "getting-started")
