from __future__ import annotations

from typing import Any

from config.settings import AppSettings
from src.infra.external.ollama_client import OllamaClient
from src.infra.external.market_data_gateway import MarketDataGateway
from src.infra.external.search_gateway import AdvancedSearchGateway
from src.infra.repo.mongo import MongoClientProvider
from src.infra.repo.redis import RedisClientProvider
from src.infra.repo.vector import VectorStoreProvider


class HealthService:
    def __init__(
        self,
        settings: AppSettings,
        mongo: MongoClientProvider,
        redis: RedisClientProvider,
        vector: VectorStoreProvider,
        ollama: OllamaClient,
        search: AdvancedSearchGateway | None = None,
        market_data: MarketDataGateway | None = None,
    ) -> None:
        self.settings = settings
        self.mongo = mongo
        self.redis = redis
        self.vector = vector
        self.ollama = ollama
        self.search = search
        self.market_data = market_data

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "app": self.settings.app_name,
            "env": self.settings.env,
            "storage_mode": "memory_fallback" if self.settings.use_memory_fallback else "external",
            "mongo": self.mongo.status(),
            "redis": self.redis.status(),
            "vector": self.vector.status(),
            "model": self.ollama.health(),
            "search": self.search.status() if self.search else {"configured": False},
            "market_data": self.market_data.status() if self.market_data else {"configured": False},
        }
