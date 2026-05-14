
from typing import Any

from langchain_core.embeddings import Embeddings
from pydantic import BaseModel, PrivateAttr

from app.infra.providers.embedding import (
    EmbeddingProvider,
    OllamaEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
)


class LangChainEmbeddings(BaseModel, Embeddings):
    """Generic LangChain Embeddings wrapper for any EmbeddingProvider."""

    provider_instance: Any = None
    _provider: EmbeddingProvider | None = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        if self.provider_instance is not None:
            self._provider = self.provider_instance

    def _get_provider(self) -> EmbeddingProvider:
        if self._provider is None:
            raise RuntimeError("No embedding provider configured")
        return self._provider

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import asyncio

        return asyncio.run(self.aembed_documents(texts))

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        provider = self._get_provider()
        return await provider.embed_batch(texts)

    def embed_query(self, text: str) -> list[float]:
        import asyncio

        return asyncio.run(self.aembed_query(text))

    async def aembed_query(self, text: str) -> list[float]:
        provider = self._get_provider()
        return await provider.embed(text)

    async def close(self) -> None:
        """Close the underlying provider."""
        if self._provider is not None:
            await self._provider.close()
            self._provider = None


class CustomOllamaEmbeddings(LangChainEmbeddings):
    """包装 OllamaEmbeddingProvider 到 LangChain Embeddings 接口（向后兼容）"""

    base_url: str
    model: str
    dims: int
    timeout: float = 60.0

    def model_post_init(self, __context: Any) -> None:
        self._provider = OllamaEmbeddingProvider(
            base_url=self.base_url,
            model=self.model,
            dims=self.dims,
            timeout=self.timeout,
        )


class OpenAICompatibleEmbeddings(LangChainEmbeddings):
    """包装 OpenAICompatibleEmbeddingProvider 到 LangChain Embeddings 接口"""

    base_url: str
    api_key: str
    model: str
    dims: int
    timeout: float = 60.0

    def model_post_init(self, __context: Any) -> None:
        self._provider = OpenAICompatibleEmbeddingProvider(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.model,
            dims=self.dims,
            timeout=self.timeout,
        )
