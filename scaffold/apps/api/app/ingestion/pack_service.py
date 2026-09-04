"""课程包摄取编排 (ADR-0006 / DESIGN §6)。

串联:CoursePackLoader → 解析 → 分块 → embedding → Chroma 入库。
AI 提取候选 taxonomy/题库见 app/ingestion/extract.py(V2 扩展,MVP 占位)。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import Settings, get_settings
from app.course_pack import CoursePackLoader
from app.ingestion.embeddings import EmbeddingClient, get_embedding_client
from app.ingestion.pack_chunker import chunk_documents
from app.ingestion.pack_parsers import parse_pack
from app.ingestion.vector_store import VectorStore


@dataclass
class IngestReport:
    course_pack_id: str
    documents: int = 0
    chunks: int = 0
    embedded: int = 0
    by_content_type: dict[str, int] = field(default_factory=dict)
    status: str = "ok"


def ingest_course_pack(
    course_pack_id: str,
    settings: Settings | None = None,
    loader: CoursePackLoader | None = None,
    embedding_client: EmbeddingClient | None = None,
    vector_store: VectorStore | None = None,
    rebuild: bool = True,
    chunk_size: int = 800,
    overlap: int = 120,
) -> IngestReport:
    settings = settings or get_settings()
    loader = loader or CoursePackLoader()
    pack = loader.load(course_pack_id)
    materials_root = loader.pack_dir(course_pack_id) / "materials"

    docs = parse_pack(pack, materials_root)
    chunks = chunk_documents(docs, chunk_size=chunk_size, overlap=overlap)

    by_type: dict[str, int] = {}
    for c in chunks:
        by_type[c.content_type] = by_type.get(c.content_type, 0) + 1

    embedding_client = embedding_client or get_embedding_client(settings)
    vector_store = vector_store or VectorStore(settings)

    if rebuild:
        vector_store.rebuild_collection(course_pack_id)

    embedded = 0
    if chunks:
        vectors = embedding_client.embed([c.text for c in chunks])
        embedded = vector_store.add_chunks(course_pack_id, chunks, vectors)

    return IngestReport(
        course_pack_id=course_pack_id,
        documents=len(docs),
        chunks=len(chunks),
        embedded=embedded,
        by_content_type=by_type,
    )
