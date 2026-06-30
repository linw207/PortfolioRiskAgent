from __future__ import annotations

import hashlib
import logging
import math
from typing import Any, Callable

from config.settings import VectorSettings
from src.infra.repo.vector import VectorStoreProvider


logger = logging.getLogger(__name__)


class VectorMemoryService:
    def __init__(
        self,
        settings: VectorSettings,
        vector: VectorStoreProvider,
        embedder: Callable[[str], list[float]] | None = None,
    ) -> None:
        self.settings = settings
        self.vector = vector
        self.embedder = embedder

    def upsert_announcement_chunks(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        ids = []
        documents = []
        metadatas = []
        embeddings = []
        for chunk in chunks:
            text = str(chunk["text"])
            chunk_id = str(chunk.get("chunk_id") or self._stable_id(text, chunk))
            ids.append(chunk_id)
            documents.append(text)
            metadatas.append(
                {
                    "symbol": str(chunk.get("symbol", "")),
                    "title": str(chunk.get("title", "")),
                    "published_at": str(chunk.get("published_at", "")),
                    "source": str(chunk.get("source", "")),
                    "url": str(chunk.get("url", "")),
                    "risk_keywords": ",".join(chunk.get("risk_keywords", [])),
                }
            )
            embeddings.append(self._embed(text))
        return self.vector.upsert(self.settings.collection_announcements, ids, documents, metadatas, embeddings)

    def search_announcement_chunks(self, query: str, symbol: str | None = None, limit: int = 5) -> dict[str, Any]:
        where = {"symbol": symbol} if symbol else None
        raw = self.vector.query(self.settings.collection_announcements, [self._embed(query)], n_results=limit, where=where)
        return normalize_chroma_query(raw)

    def upsert_agent_memory(self, memories: list[dict[str, Any]]) -> dict[str, Any]:
        ids = []
        documents = []
        metadatas = []
        embeddings = []
        for memory in memories:
            text = str(memory["text"])
            memory_id = str(memory.get("memory_id") or self._stable_id(text, memory))
            ids.append(memory_id)
            documents.append(text)
            metadatas.append(
                {
                    "user_id": str(memory.get("user_id", "")),
                    "symbol": str(memory.get("symbol", "")),
                    "task_id": str(memory.get("task_id", "")),
                    "memory_type": str(memory.get("memory_type", "")),
                    "created_at": str(memory.get("created_at", "")),
                }
            )
            embeddings.append(self._embed(text))
        return self.vector.upsert(self.settings.collection_memory, ids, documents, metadatas, embeddings)

    def search_agent_memory(self, query: str, user_id: str | None = None, symbol: str | None = None, limit: int = 5) -> dict[str, Any]:
        where = None
        if user_id and symbol:
            where = {"$and": [{"user_id": user_id}, {"symbol": symbol}]}
        elif user_id:
            where = {"user_id": user_id}
        elif symbol:
            where = {"symbol": symbol}
        raw = self.vector.query(self.settings.collection_memory, [self._embed(query)], n_results=limit, where=where)
        return normalize_chroma_query(raw)

    def _stable_id(self, text: str, metadata: dict[str, Any]) -> str:
        raw = f"{text}|{metadata}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:24]

    def _embed(self, text: str) -> list[float]:
        if self.embedder is None:
            return embed_text(text)
        try:
            return self.embedder(text)
        except Exception as exc:  # noqa: BLE001
            if not self.settings.allow_embedding_fallback:
                raise RuntimeError(f"embedding provider failed: {exc}") from exc
            logger.warning("embedding provider failed, falling back to deterministic embedding: %s", exc)
            return embed_text(text)


def embed_text(text: str, dimensions: int = 64) -> list[float]:
    """Deterministic lightweight embedding for local Chroma integration tests.

    This is not meant to be a semantic production embedding model. It provides
    stable vectors so Chroma can be used today without another model service.
    Day7 can replace it with Ollama/DashScope embeddings behind the same API.
    """

    vector = [0.0] * dimensions
    tokens = [token for token in text.lower().replace("\n", " ").split(" ") if token]
    if not tokens:
        tokens = [text.lower()]
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for index, byte in enumerate(digest):
            bucket = index % dimensions
            vector[bucket] += (byte / 255.0) - 0.5
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def normalize_chroma_query(raw: dict[str, Any]) -> dict[str, Any]:
    ids = raw.get("ids", [[]])[0]
    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]
    items = []
    for idx, item_id in enumerate(ids):
        items.append(
            {
                "id": item_id,
                "text": documents[idx] if idx < len(documents) else "",
                "metadata": metadatas[idx] if idx < len(metadatas) else {},
                "distance": distances[idx] if idx < len(distances) else None,
            }
        )
    return {"items": items}
