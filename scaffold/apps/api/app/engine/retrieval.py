"""检索适配器 (DESIGN §4.3)。

问答子图依赖一个 `Retriever` 协议:输入 query + 过滤,输出打分 chunk(dict)。
- `VectorStoreRetriever`:真实实现,embedding query → Chroma 相似检索(cosine)。
- 测试可注入任意实现(见 tests),保持子图逻辑与向量库解耦。

领域无关:检索按 course_pack_id 定位 collection,内容由摄取阶段注入。
"""

from __future__ import annotations

from typing import Protocol

from app.core.config import Settings, get_settings
from app.ingestion.embeddings import EmbeddingClient, get_embedding_client
from app.ingestion.vector_store import VectorStore


class Retriever(Protocol):
    def retrieve(
        self,
        course_pack_id: str,
        query: str,
        course_ids: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """返回打分 chunk 列表。每项含 chunk_id/text/score/metadata。"""
        ...


def _distance_to_score(distance: float) -> float:
    """cosine distance(越小越近)→ 相似度 score(0..1,越大越相关)。"""
    return round(max(0.0, 1.0 - distance), 4)


class VectorStoreRetriever:
    """真实检索:Ark/mock embedding query → Chroma。"""

    def __init__(
        self,
        settings: Settings | None = None,
        embedding_client: EmbeddingClient | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._embedding = embedding_client or get_embedding_client(self._settings)
        self._store = vector_store or VectorStore(self._settings)

    def retrieve(
        self,
        course_pack_id: str,
        query: str,
        course_ids: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        if not query.strip():
            return []
        qvec = self._embedding.embed([query])[0]
        where = {"course_id": {"$in": course_ids}} if course_ids else None
        hits = self._store.query(course_pack_id, qvec, top_k=top_k, where=where)
        out: list[dict] = []
        for h in hits:
            out.append(
                {
                    "chunk_id": h.chunk_id,
                    "text": h.text,
                    "score": _distance_to_score(h.distance),
                    "metadata": h.metadata,
                }
            )
        return out
