"""feat-004 摄取管线测试 (ADR-0003 / ADR-0006 / DESIGN §6)。

用 MockEmbeddingClient + tmp Chroma 验证 parse→chunk→embed→store→query 全链路;
用 MockLLMClient 验证 AI 候选提取(含启发式回退);
单独的真实 Ark embedding 冒烟测试默认跳过,仅在 EMBEDDING_PROVIDER=ark_multimodal
且配好 key 时运行。
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

from app.course_pack import CoursePackLoader
from app.ingestion.embeddings import (
    ArkMultimodalEmbeddingClient,
    LocalEmbeddingClient,
    MockEmbeddingClient,
)
from app.ingestion.extract import extract_candidates
from app.ingestion.pack_chunker import chunk_documents
from app.ingestion.pack_parsers import (
    ANCHOR_HEADING,
    ANCHOR_SLIDE,
    CONTENT_COURSEWARE,
    MaterialDoc,
    parse_course_materials,
    parse_html_slides,
    parse_pack,
    split_markdown_sections,
)
from app.ingestion.pack_service import ingest_course_pack
from app.ingestion.vector_store import VectorStore
from app.core.config import Settings
from app.llm import MockLLMClient

REPO_ROOT = Path(__file__).resolve().parents[4]
PACKS_ROOT = REPO_ROOT / "data" / "course_packs"
AI_AGENT_EXISTS = (PACKS_ROOT / "ai_agent" / "manifest.yaml").exists()


# --- 解析器单元 ---


def test_parse_html_slides_deshell_by_section() -> None:
    html = """
    <html><head><style>x{}</style></head><body>
      <section data-mira-slide><h1>标题一</h1><p>正文一</p></section>
      <section data-mira-slide><h1>标题二</h1><p>正文二</p></section>
      <script>console.log(1)</script>
    </body></html>
    """
    pages = parse_html_slides(html)
    assert len(pages) == 2
    assert pages[0][0] == 1 and "正文一" in pages[0][1]
    assert "console.log" not in pages[0][1]  # script 已去壳


def test_parse_html_slides_fallback_single_page() -> None:
    pages = parse_html_slides("<html><body><p>无 section</p></body></html>")
    assert len(pages) == 1
    assert "无 section" in pages[0][1]


# --- CoursewareDoc v1:标题分段 + heading anchor ---


def test_split_markdown_sections_by_heading() -> None:
    body = (
        "## 第一节 概述\n\n正文一。\n\n"
        "## 第二节 工具 {#tools}\n\n正文二。\n\n"
        "### 2.1 子节\n\n子节正文。\n"
    )
    sections = split_markdown_sections(body)
    assert [s[0] for s in sections] == ["第一节 概述", "第二节 工具", "2.1 子节"]
    # 显式锚点优先,否则 slug
    anchors = [s[1] for s in sections]
    assert anchors[1] == "tools"  # {#tools} 覆盖
    assert anchors[0]  # slug 非空


def test_split_markdown_sections_ignores_fenced_headings() -> None:
    """代码块内的 # 不当标题,避免误切。"""
    body = "## 真标题\n\n```python\n# 这是注释不是标题\nx = 1\n```\n\n正文。\n"
    sections = split_markdown_sections(body)
    assert len(sections) == 1
    assert sections[0][0] == "真标题"
    assert "# 这是注释不是标题" in sections[0][2]


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_parse_courseware_yields_heading_anchor_docs() -> None:
    """真实课件:每个标题段一个 MaterialDoc,anchor_type=heading。"""
    loader = CoursePackLoader()
    pack = loader.load("ai_agent")
    course = pack.get_course("langchain_agent")
    materials_root = loader.pack_dir("ai_agent") / "materials"
    docs = parse_course_materials(pack, course, materials_root)
    assert docs
    # 全部来自结构化课件,且带 heading anchor
    assert all(d.content_type == CONTENT_COURSEWARE for d in docs)
    assert all(d.anchor_type == ANCHOR_HEADING and d.anchor_value for d in docs)
    # 显式锚点 {#overview} 被保留
    anchors = {d.anchor_value for d in docs}
    assert "overview" in anchors
    # 附件(PPT/代码)不入检索索引
    assert not any(d.content_type == "slide" for d in docs)


# --- 分块器 ---


def test_chunker_windows_and_metadata() -> None:
    doc = MaterialDoc(
        course_pack_id="p",
        course_id="c",
        content_type="slide",
        source_path="s.html",
        text="甲" * 2000,
        slide_no=3,
        section="s p3",
        anchor_type=ANCHOR_SLIDE,
        anchor_value="3",
    )
    chunks = chunk_documents([doc], chunk_size=800, overlap=120)
    assert len(chunks) >= 2
    md = chunks[0].chroma_metadata()
    assert md["course_id"] == "c"
    assert md["slide_no"] == 3
    assert md["content_type"] == "slide"
    # anchor 元数据透传,供引用跳转
    assert md["anchor_type"] == ANCHOR_SLIDE
    assert md["anchor_value"] == "3"
    # id 稳定
    again = chunk_documents([doc], chunk_size=800, overlap=120)
    assert [c.chunk_id for c in chunks] == [c.chunk_id for c in again]


def test_chunker_propagates_heading_anchor() -> None:
    """课件标题段分块后,每块都带同一 heading anchor。"""
    doc = MaterialDoc(
        course_pack_id="p",
        course_id="c",
        content_type=CONTENT_COURSEWARE,
        source_path="c1.md",
        text="核心概念\n\n" + "内容 " * 400,
        section="核心概念",
        anchor_type=ANCHOR_HEADING,
        anchor_value="core-concept",
    )
    chunks = chunk_documents([doc], chunk_size=800, overlap=0)
    assert chunks
    for c in chunks:
        md = c.chroma_metadata()
        assert md["anchor_type"] == ANCHOR_HEADING
        assert md["anchor_value"] == "core-concept"


# --- 向量库 + query(mock embedding，tmp Chroma) ---


def test_vector_store_roundtrip(tmp_path) -> None:
    doc_a = MaterialDoc("p", "c", "slide", "a.html", "LangGraph 的 State 与节点边", slide_no=1)
    doc_b = MaterialDoc("p", "c", "slide", "b.html", "向量数据库与相似度检索", slide_no=2)
    chunks = chunk_documents([doc_a, doc_b], chunk_size=800, overlap=0)

    emb = MockEmbeddingClient(dim=64)
    store = VectorStore(persist_dir=str(tmp_path / "chroma"))
    store.rebuild_collection("p")
    vectors = emb.embed([c.text for c in chunks])
    n = store.add_chunks("p", chunks, vectors)
    assert n == len(chunks)
    assert store.count("p") == len(chunks)

    # 用其中一个 chunk 文本作查询，应最相近命中自身
    q = emb.embed([doc_a.text])[0]
    hits = store.query("p", q, top_k=2)
    assert hits
    assert hits[0].text == doc_a.text
    assert hits[0].metadata["course_id"] == "c"


def test_vector_store_where_filter(tmp_path) -> None:
    docs = [
        MaterialDoc("p", "c1", "slide", "a.html", "内容 A"),
        MaterialDoc("p", "c2", "slide", "b.html", "内容 B"),
    ]
    chunks = chunk_documents(docs, chunk_size=800, overlap=0)
    emb = MockEmbeddingClient(dim=32)
    store = VectorStore(persist_dir=str(tmp_path / "chroma"))
    store.rebuild_collection("p")
    store.add_chunks("p", chunks, emb.embed([c.text for c in chunks]))

    hits = store.query("p", emb.embed(["内容 A"])[0], top_k=5, where={"course_id": "c1"})
    assert hits
    assert all(h.metadata["course_id"] == "c1" for h in hits)


# --- AI 提取(mock LLM，走启发式回退) ---


def test_extract_candidates_fallback_heuristic() -> None:
    docs = [
        MaterialDoc("p", "c", "lecture_note", "n1.md", "Agent 循环: 感知-规划-行动", section="agent_loop"),
        MaterialDoc("p", "c", "slide", "s.html", "工具调用与 ReAct", section="tools", slide_no=1),
    ]
    # MockLLMClient 不产 JSON → 走 section 启发式回退
    res = extract_candidates("p", docs, llm=MockLLMClient())
    assert res.course_pack_id == "p"
    assert res.topics
    names = {t.name for t in res.topics}
    assert "agent_loop" in names or "tools" in names
    # 候选状态
    assert all(t.status == "candidate" for t in res.topics)


def test_extract_candidates_parses_llm_json() -> None:
    class _JsonLLM(MockLLMClient):
        def complete(self, prompt, system=None, **kwargs):
            return (
                '```json\n{"topics": [{"name": "状态图", "summary": "StateGraph 基础"}],'
                ' "questions": [{"prompt": "画出核心循环", "topic_name": "状态图",'
                ' "difficulty": "medium"}]}\n```'
            )

    res = extract_candidates("p", [MaterialDoc("p", "c", "slide", "s.html", "文本")], llm=_JsonLLM())
    assert [t.name for t in res.topics] == ["状态图"]
    assert res.questions and res.questions[0].topic_name == "状态图"
    assert res.questions[0].status == "candidate"


# --- 端到端 ingest(真实课程包 + mock embedding) ---


@pytest.mark.skipif(not AI_AGENT_EXISTS, reason="ai_agent 课程包不存在")
def test_ingest_real_pack_with_mock_embedding(tmp_path) -> None:
    store = VectorStore(persist_dir=str(tmp_path / "chroma"))
    report = ingest_course_pack(
        "ai_agent",
        loader=CoursePackLoader(),
        embedding_client=MockEmbeddingClient(dim=64),
        vector_store=store,
        rebuild=True,
    )
    assert report.status == "ok"
    assert report.documents > 0
    assert report.chunks > 0
    assert report.embedded == report.chunks
    assert store.count("ai_agent") == report.chunks

    # 检索一条与 langgraph 有关的内容
    q = MockEmbeddingClient(dim=64).embed(["langgraph state graph"])[0]
    hits = store.query("ai_agent", q, top_k=3)
    assert hits


# --- 真实 Ark 多模态 embedding 冒烟(仅配置齐备时) ---

_ARK_READY = (
    os.getenv("EMBEDDING_PROVIDER") == "ark_multimodal"
    and bool(os.getenv("EMBEDDING_API_KEY"))
    and bool(os.getenv("EMBEDDING_BASE_URL"))
)


@pytest.mark.skipif(not _ARK_READY, reason="未配置真实 Ark 多模态 embedding")
def test_ark_multimodal_embedding_smoke() -> None:
    settings = Settings(_env_file=str(REPO_ROOT / ".env"))
    client = ArkMultimodalEmbeddingClient(settings)
    vecs = client.embed(["向量检索", "LangGraph 状态机"])
    assert len(vecs) == 2
    assert len(vecs[0]) == len(vecs[1]) > 0


# --- 本地离线向量模型冒烟(仅安装了 sentence-transformers 时运行,不需要网络配置) ---

_LOCAL_EMBEDDING_AVAILABLE = importlib.util.find_spec("sentence_transformers") is not None


@pytest.mark.skipif(
    not _LOCAL_EMBEDDING_AVAILABLE,
    reason="未安装 sentence-transformers(uv pip install -e '.[dev,local-embedding]')",
)
def test_local_embedding_client_semantic_direction() -> None:
    """本地向量模型必须产出真实语义方向,而非 mock 的纯 hash 伪向量。"""
    settings = Settings(embedding_provider="local")
    client = LocalEmbeddingClient(settings)
    related_a, unrelated, related_b = client.embed(
        [
            "LangGraph 的 StateGraph 是一种状态图编排方式",
            "苹果是一种水果,富含维生素",
            "StateGraph 通过节点和边定义状态在图中的流转",
        ]
    )
    sim_related = sum(a * b for a, b in zip(related_a, related_b))
    sim_unrelated = sum(a * b for a, b in zip(related_a, unrelated))
    assert sim_related > sim_unrelated
    assert client.dim == len(related_a) > 0
