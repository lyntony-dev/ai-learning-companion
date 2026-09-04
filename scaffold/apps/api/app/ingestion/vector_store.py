"""Chroma 向量库封装 (DESIGN §5)。

持久化到 CHROMA_PERSIST_DIR。按 course_pack_id 分 collection。
写入时用外部预算好的向量(embedding 客户端产出),检索时同样传 query 向量,
使 embedding provider 可切换(mock / ark_multimodal)且检索与索引维度一致。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, get_settings
from app.ingestion.pack_chunker import Chunk


@dataclass
class Retrieved:
    chunk_id: str
    text: str
    metadata: dict
    distance: float


def _collection_name(course_pack_id: str) -> str:
    return f"pack_{course_pack_id}"


class VectorStore:
    """Chroma 持久化向量库。"""

    def __init__(self, settings: Settings | None = None, persist_dir: str | None = None) -> None:
        settings = settings or get_settings()
        self._persist_dir = persist_dir or settings.chroma_persist_dir

    def _client(self):
        import chromadb

        return chromadb.PersistentClient(path=self._persist_dir)

    def _get_collection(self, course_pack_id: str, create: bool = True):
        client = self._client()
        name = _collection_name(course_pack_id)
        if create:
            return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
        return client.get_collection(name=name)

    def rebuild_collection(self, course_pack_id: str) -> None:
        """清空并重建某课程包的 collection。"""
        import chromadb

        client = self._client()
        name = _collection_name(course_pack_id)
        try:
            client.delete_collection(name=name)
        except Exception:
            pass
        client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

    def add_chunks(
        self, course_pack_id: str, chunks: list[Chunk], vectors: list[list[float]]
    ) -> int:
        if not chunks:
            return 0
        if len(chunks) != len(vectors):
            raise ValueError("chunks 与 vectors 数量不一致")
        collection = self._get_collection(course_pack_id, create=True)
        collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=vectors,
            documents=[c.text for c in chunks],
            metadatas=[c.chroma_metadata() for c in chunks],
        )
        return len(chunks)

    def count(self, course_pack_id: str) -> int:
        try:
            return self._get_collection(course_pack_id, create=False).count()
        except Exception:
            return 0

    def query(
        self,
        course_pack_id: str,
        query_vector: list[float],
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[Retrieved]:
        try:
            collection = self._get_collection(course_pack_id, create=False)
        except Exception:
            return []
        res = collection.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where or None,
        )
        out: list[Retrieved] = []
        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for i in range(len(ids)):
            out.append(
                Retrieved(
                    chunk_id=ids[i],
                    text=docs[i],
                    metadata=metas[i] or {},
                    distance=dists[i] if i < len(dists) else 0.0,
                )
            )
        return out
