from __future__ import annotations

from typing import Any

from config.settings import MongoSettings


class MongoClientProvider:
    """Lazy Motor client boundary.

    Day1-2 only establishes the production boundary and health check. Concrete
    repositories can be added without changing application services.
    """

    def __init__(self, settings: MongoSettings) -> None:
        self.settings = settings
        self._client: Any | None = None
        self._sync_client: Any | None = None

    def client(self) -> Any:
        if self._client is None:
            try:
                from motor.motor_asyncio import AsyncIOMotorClient
            except ImportError as exc:
                raise RuntimeError("motor is not installed") from exc
            self._client = AsyncIOMotorClient(
                self.settings.uri,
                serverSelectionTimeoutMS=self.settings.connect_timeout_ms,
            )
        return self._client

    def database(self) -> Any:
        return self.client()[self.settings.database]

    def sync_client(self) -> Any:
        if self._sync_client is None:
            try:
                from pymongo import MongoClient
            except ImportError as exc:
                raise RuntimeError("pymongo is not installed") from exc
            self._sync_client = MongoClient(
                self.settings.uri,
                serverSelectionTimeoutMS=self.settings.connect_timeout_ms,
            )
        return self._sync_client

    def sync_database(self) -> Any:
        return self.sync_client()[self.settings.database]

    def status(self) -> dict[str, Any]:
        if not self.settings.enabled:
            return {"enabled": False, "status": "disabled"}
        try:
            client = self.sync_client()
            return {
                "enabled": True,
                "status": "configured",
                "database": self.settings.database,
                "uri": self.settings.uri,
                "client": client.__class__.__name__,
            }
        except RuntimeError as exc:
            return {"enabled": True, "status": "missing_dependency", "error": str(exc)}
