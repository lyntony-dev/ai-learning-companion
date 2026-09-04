"""LLM 客户端 (ADR-0003 / DESIGN §7)。

Ark VLM 走标准 OpenAI 兼容 /chat/completions(与 embedding 的多模态接口不同)。
两种 provider(LLM_PROVIDER):
  - openai_compatible: 真实调用 Ark /chat/completions
  - mock: 确定性回显,供离线/CI/单测使用

被 AI 提取(ingestion/extract)、Answer/Grader/Router 等节点复用。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import Settings, get_settings


class LLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str, system: str | None = None, **kwargs) -> str: ...


class MockLLMClient(LLMClient):
    """确定性伪回答:回显 prompt 摘要,便于离线跑通与断言。"""

    def complete(self, prompt: str, system: str | None = None, **kwargs) -> str:
        head = prompt.strip().replace("\n", " ")[:120]
        return f"[MOCK-LLM] {head}"


class ArkChatClient(LLMClient):
    """Ark /chat/completions 客户端(OpenAI 兼容)。"""

    def __init__(self, settings: Settings) -> None:
        if not settings.llm_base_url or not settings.llm_api_key:
            raise ValueError("openai_compatible 需要 LLM_BASE_URL 与 LLM_API_KEY")
        self._base_url = settings.llm_base_url.rstrip("/")
        self._api_key = settings.llm_api_key
        self._model = settings.llm_model
        self._timeout = settings.llm_timeout_seconds
        self._max_tokens = settings.llm_max_tokens
        self._temperature = settings.llm_temperature

    def complete(self, prompt: str, system: str | None = None, **kwargs) -> str:
        import httpx

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "temperature": kwargs.get("temperature", self._temperature),
        }
        url = f"{self._base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]


def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    if settings.llm_provider == "openai_compatible":
        return ArkChatClient(settings)
    return MockLLMClient()
