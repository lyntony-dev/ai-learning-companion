"""Embedding 客户端 (ADR-0003 / DESIGN §7)。

Ark 的 embedding 模型是多模态(doubao-embedding-vision),必须走
POST /embeddings/multimodal,input 为 [{"type":"text","text":...}],
不支持标准 /embeddings 文本接口。

三种 provider(EMBEDDING_PROVIDER):
  - ark_multimodal: 真实调用 Ark 多模态接口
  - local: 本地离线向量模型(sentence-transformers),不需要任何 API key
  - mock: 确定性伪向量,供离线/CI/单测使用(不联网,也不代表真实语义)

多模态接口对图片输入天然支持,V2 做 PPT 截图/图表索引时可复用同一客户端。
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Any

from app.core.config import Settings, get_settings


class EmbeddingClient(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """返回与 texts 等长的向量列表。"""

    @property
    @abstractmethod
    def dim(self) -> int: ...


class MockEmbeddingClient(EmbeddingClient):
    """确定性伪向量:同文本恒等向量,便于测试与离线跑通。"""

    def __init__(self, dim: int = 768) -> None:
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def _vec(self, text: str) -> list[float]:
        # 用 hash 稳定展开成 dim 维 [0,1) 向量
        out: list[float] = []
        seed = text.encode("utf-8")
        counter = 0
        while len(out) < self._dim:
            h = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            for b in h:
                out.append(b / 255.0)
                if len(out) >= self._dim:
                    break
            counter += 1
        return out

    @property
    def dim(self) -> int:
        return self._dim


class ArkMultimodalEmbeddingClient(EmbeddingClient):
    """Ark /embeddings/multimodal 客户端(ADR-0003)。"""

    def __init__(self, settings: Settings, batch_size: int | None = None) -> None:
        if not settings.embedding_base_url or not settings.embedding_api_key:
            raise ValueError("ark_multimodal 需要 EMBEDDING_BASE_URL 与 EMBEDDING_API_KEY")
        self._base_url = settings.embedding_base_url.rstrip("/")
        self._api_key = settings.embedding_api_key
        self._model = settings.embedding_model
        self._batch_size = batch_size or settings.embedding_batch_size
        self._dim: int | None = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        import httpx

        vectors: list[list[float]] = []
        url = f"{self._base_url}/embeddings/multimodal"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        # 多模态接口按单条 input 组织;逐条请求以保持稳定
        with httpx.Client(timeout=60.0) as client:
            for text in texts:
                payload = {
                    "model": self._model,
                    "input": [{"type": "text", "text": text}],
                }
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                vec = self._extract_vector(data)
                if self._dim is None:
                    self._dim = len(vec)
                vectors.append(vec)
        return vectors

    @staticmethod
    def _extract_vector(data: dict) -> list[float]:
        # 兼容 {"data":{"embedding":[...]}} 与 {"data":[{"embedding":[...]}]}
        d = data.get("data")
        if isinstance(d, dict):
            return d["embedding"]
        if isinstance(d, list) and d:
            return d[0]["embedding"]
        raise ValueError(f"无法从响应解析 embedding: keys={list(data)}")

    @property
    def dim(self) -> int:
        if self._dim is None:
            # 触发一次探测
            self._dim = len(self.embed(["_probe_"])[0])
        return self._dim


_LOCAL_MODEL_CACHE: dict[str, Any] = {}


def _load_local_model(model_name: str) -> Any:
    """加载并进程内缓存 sentence-transformers 模型,避免每次请求重复加载。

    get_retriever 每个请求都会重新构造 EmbeddingClient(见 app/engine/retrieval.py),
    若不做模块级缓存,LocalEmbeddingClient 会在每次问答请求时都重新读盘加载模型。
    """
    if model_name not in _LOCAL_MODEL_CACHE:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - 依赖未安装时给出明确指引
            raise RuntimeError(
                "EMBEDDING_PROVIDER=local 需要安装 sentence-transformers:"
                "uv pip install -e '.[dev,local-embedding]'"
            ) from exc
        _LOCAL_MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _LOCAL_MODEL_CACHE[model_name]


class LocalEmbeddingClient(EmbeddingClient):
    """本地离线向量模型(sentence-transformers),不需要任何 API key,不联网即可跑。

    默认 BAAI/bge-small-zh-v1.5:中文语义检索效果好、体积小(~95MB),
    首次调用时从 HuggingFace Hub 自动下载并缓存到 ~/.cache/huggingface。
    """

    def __init__(self, settings: Settings) -> None:
        self._model_name = settings.local_embedding_model
        self._model = _load_local_model(self._model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=False
        )
        return vectors.tolist()

    @property
    def dim(self) -> int:
        return self._model.get_embedding_dimension()


def get_embedding_client(settings: Settings | None = None) -> EmbeddingClient:
    """按 EMBEDDING_PROVIDER 选择客户端。"""
    settings = settings or get_settings()
    provider = settings.embedding_provider
    if provider == "ark_multimodal":
        return ArkMultimodalEmbeddingClient(settings)
    if provider == "local":
        return LocalEmbeddingClient(settings)
    return MockEmbeddingClient(dim=settings.embedding_dim)
