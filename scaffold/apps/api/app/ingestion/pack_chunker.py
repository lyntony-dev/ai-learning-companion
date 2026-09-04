"""课程包分块器 (ADR-0006 / DESIGN §6)。

把 MaterialDoc 切成带完整元数据的检索单元 Chunk。
按字符窗口 + 重叠切分(近似 token-aware;中文按字符更稳)。
每个 chunk 可追溯 course_id / slide_no / section / content_type / source_path。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

from app.ingestion.pack_parsers import MaterialDoc

DEFAULT_CHUNK_SIZE = 800
DEFAULT_OVERLAP = 120


@dataclass
class Chunk:
    chunk_id: str
    course_pack_id: str
    course_id: str
    content_type: str
    source_path: str
    text: str
    slide_no: int | None = None
    section: str = ""
    ordinal: int = 0
    anchor_type: str = "none"
    anchor_value: str = ""
    metadata: dict = field(default_factory=dict)

    def chroma_metadata(self) -> dict:
        """Chroma 只接受标量元数据值。"""
        md = {
            "course_pack_id": self.course_pack_id,
            "course_id": self.course_id,
            "content_type": self.content_type,
            "source_path": self.source_path,
            "section": self.section,
            "ordinal": self.ordinal,
            "anchor_type": self.anchor_type,
            "anchor_value": self.anchor_value,
        }
        if self.slide_no is not None:
            md["slide_no"] = self.slide_no
        return md


def _stable_id(doc: MaterialDoc, ordinal: int) -> str:
    raw = (
        f"{doc.course_pack_id}:{doc.course_id}:{doc.source_path}:"
        f"{doc.slide_no}:{doc.anchor_value}:{ordinal}"
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"chunk_{digest}"


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """字符窗口 + 重叠切分。"""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    step = max(1, chunk_size - overlap)
    pieces: list[str] = []
    start = 0
    while start < len(text):
        piece = text[start : start + chunk_size].strip()
        if piece:
            pieces.append(piece)
        start += step
    return pieces


def chunk_document(
    doc: MaterialDoc,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for ordinal, piece in enumerate(split_text(doc.text, chunk_size, overlap)):
        chunks.append(
            Chunk(
                chunk_id=_stable_id(doc, ordinal),
                course_pack_id=doc.course_pack_id,
                course_id=doc.course_id,
                content_type=doc.content_type,
                source_path=doc.source_path,
                text=piece,
                slide_no=doc.slide_no,
                section=doc.section,
                ordinal=ordinal,
                anchor_type=doc.anchor_type,
                anchor_value=doc.anchor_value,
                metadata=dict(doc.metadata),
            )
        )
    return chunks


def chunk_documents(
    docs: list[MaterialDoc],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    out: list[Chunk] = []
    for doc in docs:
        out.extend(chunk_document(doc, chunk_size, overlap))
    return out
