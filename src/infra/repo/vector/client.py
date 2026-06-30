from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any

from config.settings import VectorSettings


class VectorStoreProvider:
    """Vector DB boundary for announcement RAG and memory.

    Chroma is the first implementation target because it is local-first and
    simple for a resume project demo. Milvus/Qdrant can be added behind the
    same provider contract later.
    """

    def __init__(self, settings: VectorSettings) -> None:
        self.settings = settings
        self._client: Any | None = None

    def client(self) -> Any:
        if self.settings.mode == "http":
            return {"mode": "http", "url": self.settings.http_url}
        if self._client is None:
            if self.settings.provider != "chroma":
                raise RuntimeError(f"unsupported vector provider: {self.settings.provider}")
            try:
                import chromadb
            except ImportError as exc:
                raise RuntimeError("chromadb is not installed") from exc
            self._client = chromadb.PersistentClient(path=self.settings.persist_dir)
        return self._client

    def status(self) -> dict[str, Any]:
        if not self.settings.enabled:
            return {"enabled": False, "status": "disabled"}
        try:
            if self.settings.mode == "http":
                heartbeat = self._http_heartbeat()
                return {
                    "enabled": True,
                    "status": "configured",
                    "provider": self.settings.provider,
                    "mode": "http",
                    "http_url": self.settings.http_url,
                    "heartbeat": heartbeat,
                    "collections": [
                        self.settings.collection_announcements,
                        self.settings.collection_memory,
                    ],
                }
            self.client()
            return {
                "enabled": True,
                "status": "configured",
                "provider": self.settings.provider,
                "mode": self.settings.mode,
                "persist_dir": self.settings.persist_dir,
                "collections": [
                    self.settings.collection_announcements,
                    self.settings.collection_memory,
                ],
            }
        except RuntimeError as exc:
            return {"enabled": True, "status": "missing_dependency", "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"enabled": True, "status": "unavailable", "error": str(exc)}

    def _http_heartbeat(self) -> dict[str, Any]:
        candidates = [
            self.settings.http_url.rstrip("/") + "/api/v1/heartbeat",
            self.settings.http_url.rstrip("/") + "/api/v2/heartbeat",
        ]
        last_error = ""
        for url in candidates:
            try:
                with urllib.request.urlopen(url, timeout=3) as response:
                    body = response.read().decode("utf-8")
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    payload = {"raw": body}
                return {"url": url, "response": payload}
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
        raise RuntimeError(last_error)

    def get_or_create_collection(self, name: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        existing = self.get_collection(name)
        if existing:
            return existing
        status, body = self._http_request("POST", "/api/v1/collections", {"name": name, "metadata": metadata or {}})
        if status not in {200, 201}:
            raise RuntimeError(f"failed to create Chroma collection {name}: {status} {body}")
        return json.loads(body)

    def get_collection(self, name: str) -> dict[str, Any] | None:
        status, body = self._http_request("GET", "/api/v1/collections")
        if status != 200:
            raise RuntimeError(f"failed to list Chroma collections: {status} {body}")
        for item in json.loads(body):
            if item.get("name") == name:
                return item
        return None

    def upsert(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> dict[str, Any]:
        collection = self.get_or_create_collection(collection_name, {"project": "PortfolioRiskAgent"})
        path = f"/api/v1/collections/{collection['id']}/upsert"
        status, body = self._http_request(
            "POST",
            path,
            {"ids": ids, "documents": documents, "metadatas": metadatas, "embeddings": embeddings},
        )
        if status not in {200, 201}:
            raise RuntimeError(f"failed to upsert Chroma documents: {status} {body}")
        return {"collection": collection_name, "ids": ids, "status": status, "body": body}

    def query(
        self,
        collection_name: str,
        query_embeddings: list[list[float]],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        collection = self.get_or_create_collection(collection_name, {"project": "PortfolioRiskAgent"})
        payload: dict[str, Any] = {
            "query_embeddings": query_embeddings,
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            payload["where"] = where
        status, body = self._http_request("POST", f"/api/v1/collections/{collection['id']}/query", payload)
        if status != 200:
            raise RuntimeError(f"failed to query Chroma documents: {status} {body}")
        return json.loads(body)

    def _http_request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, str]:
        if self.settings.mode != "http":
            raise RuntimeError("HTTP vector mode is required for this operation")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self.settings.http_url.rstrip("/") + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")
