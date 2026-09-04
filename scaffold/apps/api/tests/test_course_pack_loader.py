"""feat-003 CoursePackLoader 测试 (ADR-0006)。

一半用真实的 ai_agent 课程包(端到端确认迁移+约定文件正确),
一半用 tmp 构造的最小包验证错误路径(缺 manifest / id 不一致 / 资料缺失)。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.course_pack import ArtifactStatus, CoursePackError, CoursePackLoader

REPO_ROOT = Path(__file__).resolve().parents[4]
PACKS_ROOT = REPO_ROOT / "data" / "course_packs"
AI_AGENT_EXISTS = (PACKS_ROOT / "ai_agent" / "manifest.yaml").exists()


# --- 真实 ai_agent 课程包 ---


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_load_real_ai_agent_pack() -> None:
    loader = CoursePackLoader()
    pack = loader.load("ai_agent")

    assert pack.course_pack_id == "ai_agent"
    # 四门课
    ids = {c.course_id for c in pack.courses}
    assert ids == {"langchain_agent", "langgraph_multiagent", "mcp_agent", "rag_vector"}
    # 里程碑序列(F)
    assert pack.milestone_ids() == [
        "topic_selection",
        "architecture_design",
        "core_loop",
        "tool_integration",
        "evaluation",
        "delivery",
    ]
    # taxonomy 候选 + 知识点非空
    assert pack.taxonomy.status is ArtifactStatus.CANDIDATE
    assert "langgraph.state" in pack.topic_ids()
    # rubric 专项维度
    assert "rag_vector" in pack.rubric.by_course


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_capstone_guidance_fields_present() -> None:
    """项目说明书与里程碑引导字段应从 manifest 解析出来(学生端展示用)。

    sample_report 已随立项向导重设计从 manifest 移除,schema 保留为可选空串(向后兼容)。
    """
    pack = CoursePackLoader().load("ai_agent")
    assert pack.capstone is not None
    assert pack.capstone.overview.strip()
    assert pack.capstone.final_deliverable.strip()
    first = pack.capstone.milestones[0]
    assert first.id == "topic_selection"
    assert first.deliverable.strip()
    assert first.hint.strip()


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_available_packs_lists_ai_agent() -> None:
    assert "ai_agent" in CoursePackLoader().available_packs()


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_get_course_returns_named_course() -> None:
    pack = CoursePackLoader().load("ai_agent")
    course = pack.get_course("mcp_agent")
    assert course is not None
    assert course.name == "MCP 工具接入"
    assert course.materials.lecture_note is not None


# --- 错误路径(tmp 构造) ---


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_missing_manifest_raises(tmp_path) -> None:
    loader = CoursePackLoader(packs_root=tmp_path)
    (tmp_path / "empty_pack").mkdir()
    with pytest.raises(CoursePackError, match="缺少 manifest"):
        loader.load("empty_pack")


def test_id_mismatch_raises(tmp_path) -> None:
    _write(
        tmp_path / "p1" / "manifest.yaml",
        "course_pack_id: other\nname: x\ncourses: []\n",
    )
    with pytest.raises(CoursePackError, match="不一致"):
        CoursePackLoader(packs_root=tmp_path).load("p1")


def test_missing_material_raises(tmp_path) -> None:
    _write(
        tmp_path / "p2" / "manifest.yaml",
        "course_pack_id: p2\nname: x\n"
        "courses:\n"
        "  - course_id: c1\n"
        "    name: C1\n"
        "    materials:\n"
        "      lecture_note: notes/missing.md\n",
    )
    with pytest.raises(CoursePackError, match="资料不存在"):
        CoursePackLoader(packs_root=tmp_path).load("p2")


def test_minimal_pack_loads(tmp_path) -> None:
    _write(
        tmp_path / "p3" / "manifest.yaml",
        "course_pack_id: p3\nname: 最小包\ncourses: []\n",
    )
    pack = CoursePackLoader(packs_root=tmp_path).load("p3")
    assert pack.name == "最小包"
    assert pack.courses == []
    assert pack.capstone is None
    assert pack.taxonomy.topics == []


def test_capstone_without_guidance_defaults_empty(tmp_path) -> None:
    """未声明引导字段的旧格式 capstone 仍可加载,引导字段回退空串(向后兼容)。"""
    _write(
        tmp_path / "p4" / "manifest.yaml",
        (
            "course_pack_id: p4\nname: 旧包\ncourses: []\n"
            "capstone:\n  name: 老项目\n  milestones:\n"
            "    - id: m1\n      name: 里程碑一\n"
        ),
    )
    pack = CoursePackLoader(packs_root=tmp_path).load("p4")
    assert pack.capstone is not None
    assert pack.capstone.overview == ""
    assert pack.capstone.background == ""
    assert pack.capstone.final_deliverable == ""
    m1 = pack.capstone.milestones[0]
    assert m1.deliverable == ""
    assert m1.hint == ""
    assert m1.sample_report == ""


# --- CoursewareDoc v1(结构化课件)---


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_real_langchain_course_has_courseware() -> None:
    """真实 ai_agent 包:langchain_agent 已转换为结构化课件,原始资料降为附件。"""
    pack = CoursePackLoader().load("ai_agent")
    course = pack.get_course("langchain_agent")
    assert course is not None
    assert course.courseware is not None
    assert course.courseware.path == "langchain_agent.md"
    assert course.courseware.title == "LangChain Agent 基础"
    # frontmatter 声明的附件(PPT / 代码)都被解析出来
    kinds = {a.kind for a in course.courseware.attachments}
    assert "slides" in kinds and "code" in kinds


def test_courseware_frontmatter_parsed(tmp_path) -> None:
    """课件正文头部 frontmatter 提供 title/version/attachments,加载时解析。"""
    _write(
        tmp_path / "p" / "manifest.yaml",
        "course_pack_id: p\nname: x\n"
        "courses:\n"
        "  - course_id: c1\n"
        "    name: C1\n"
        "    courseware: c1.md\n"
        "    materials:\n"
        "      slides:\n"
        "        - slides/deck.html\n",
    )
    _write(tmp_path / "p" / "materials" / "slides" / "deck.html", "<html></html>")
    _write(
        tmp_path / "p" / "courseware" / "c1.md",
        "---\n"
        "course_id: c1\n"
        "title: 课件标题\n"
        "version: v2\n"
        "attachments:\n"
        "  - kind: slides\n"
        "    path: slides/deck.html\n"
        "    title: 幻灯片\n"
        "---\n\n"
        "## 第一节\n\n正文。\n",
    )
    pack = CoursePackLoader(packs_root=tmp_path).load("p")
    cw = pack.get_course("c1").courseware
    assert cw is not None
    assert cw.title == "课件标题"
    assert cw.version == "v2"
    assert cw.attachments[0].path == "slides/deck.html"


def test_courseware_missing_file_raises(tmp_path) -> None:
    _write(
        tmp_path / "p" / "manifest.yaml",
        "course_pack_id: p\nname: x\n"
        "courses:\n"
        "  - course_id: c1\n"
        "    name: C1\n"
        "    courseware: missing.md\n",
    )
    with pytest.raises(CoursePackError, match="课件不存在"):
        CoursePackLoader(packs_root=tmp_path).load("p")


def test_courseware_course_id_mismatch_raises(tmp_path) -> None:
    _write(
        tmp_path / "p" / "manifest.yaml",
        "course_pack_id: p\nname: x\n"
        "courses:\n"
        "  - course_id: c1\n"
        "    name: C1\n"
        "    courseware: c1.md\n",
    )
    _write(
        tmp_path / "p" / "courseware" / "c1.md",
        "---\ncourse_id: other\ntitle: T\n---\n\n## 节\n\n正文\n",
    )
    with pytest.raises(CoursePackError, match="不一致"):
        CoursePackLoader(packs_root=tmp_path).load("p")


def test_courseware_missing_attachment_raises(tmp_path) -> None:
    _write(
        tmp_path / "p" / "manifest.yaml",
        "course_pack_id: p\nname: x\n"
        "courses:\n"
        "  - course_id: c1\n"
        "    name: C1\n"
        "    courseware: c1.md\n",
    )
    _write(
        tmp_path / "p" / "courseware" / "c1.md",
        "---\ncourse_id: c1\nattachments:\n  - kind: slides\n    path: slides/gone.html\n---\n\n## 节\n\n正文\n",
    )
    with pytest.raises(CoursePackError, match="附件不存在"):
        CoursePackLoader(packs_root=tmp_path).load("p")


# --- 预置题库 questions/*.yaml ---


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_real_pack_has_preset_questions_with_difficulty() -> None:
    """真实 ai_agent 包:questions/ 已提供带难度的预置题,topic_id 均在 taxonomy 内。"""
    pack = CoursePackLoader().load("ai_agent")
    qs = pack.questions.questions
    assert qs, "预置题库应非空"
    valid_topics = set(pack.topic_ids())
    assert all(q.topic_id in valid_topics for q in qs)
    difficulties = {q.difficulty.value for q in qs}
    assert {"easy", "medium", "hard"} <= difficulties  # 三档难度齐全


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_real_pack_rubric_by_course_uses_dimension_keys() -> None:
    """rubric by_course 修复后:dimensions 引用默认 key + 课程额外维度。"""
    pack = CoursePackLoader().load("ai_agent")
    default_keys = {d.key for d in pack.rubric.default_dimensions}
    rag = pack.rubric.by_course["rag_vector"]
    assert all(k in default_keys for k in rag.dimensions)
    assert rag.extra_dimensions  # RAG 有专项维度(分块/检索/rerank/评估)
    extra_keys = {d.key for d in rag.extra_dimensions}
    assert "chunking" in extra_keys


def test_questions_missing_dir_returns_empty(tmp_path) -> None:
    """无 questions/ 目录 → 空题库(向后兼容)。"""
    _write(tmp_path / "p" / "manifest.yaml", "course_pack_id: p\nname: x\ncourses: []\n")
    pack = CoursePackLoader(packs_root=tmp_path).load("p")
    assert pack.questions.questions == []


def test_questions_unknown_topic_raises(tmp_path) -> None:
    """题目 topic_id 不在 taxonomy → fail fast。"""
    _write(tmp_path / "p" / "manifest.yaml", "course_pack_id: p\nname: x\ncourses: []\n")
    _write(
        tmp_path / "p" / "taxonomy.yaml",
        "topics:\n  - id: t.a\n    name: A\n    course_id: c1\n",
    )
    _write(
        tmp_path / "p" / "questions" / "c1.yaml",
        "questions:\n  - topic_id: t.nope\n    prompt: 问题?\n",
    )
    with pytest.raises(CoursePackError, match="不在 taxonomy"):
        CoursePackLoader(packs_root=tmp_path).load("p")


def test_rubric_unknown_dimension_key_raises(tmp_path) -> None:
    """by_course 引用未知默认维度 key → fail fast(防散文/拼写静默失效)。"""
    _write(tmp_path / "p" / "manifest.yaml", "course_pack_id: p\nname: x\ncourses: []\n")
    _write(
        tmp_path / "p" / "rubric.yaml",
        "default:\n  dimensions:\n    - key: correctness\n      name: 正确性\n      weight: 1.0\n"
        "by_course:\n  c1:\n    dimensions:\n      - nonexistent\n",
    )
    with pytest.raises(CoursePackError, match="未知维度"):
        CoursePackLoader(packs_root=tmp_path).load("p")
