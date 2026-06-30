from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from config.settings import ModelSettings


class OllamaClient:
    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings

    def health(self) -> dict[str, Any]:
        url = self.settings.base_url.rstrip("/") + "/api/tags"
        try:
            with urllib.request.urlopen(url, timeout=self.settings.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return {
                "available": True,
                "base_url": self.settings.base_url,
                "configured_model": self.settings.model_name,
                "configured_embedding_model": self.settings.embedding_model_name,
                "models": [item.get("name", "") for item in payload.get("models", [])],
            }
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return {
                "available": False,
                "base_url": self.settings.base_url,
                "configured_model": self.settings.model_name,
                "configured_embedding_model": self.settings.embedding_model_name,
                "error": str(exc),
            }

    def chat(self, messages: list[dict[str, str]]) -> str:
        """Call Ollama's OpenAI-compatible chat endpoint.

        Falls back to `/api/generate` because some local Ollama deployments
        expose only the native API.
        """
        try:
            return self._chat_openai_compatible(messages)
        except Exception:
            prompt = "\n".join(f"{item.get('role', 'user')}: {item.get('content', '')}" for item in messages)
            return self.generate(prompt)

    def generate(
        self,
        prompt: str,
        system: str = "",
        think: bool | None = None,
        num_predict: int | None = None,
    ) -> str:
        payload = {
            "model": self.settings.model_name,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "temperature": self.settings.temperature,
            },
        }
        if think is not None:
            payload["think"] = think
        if num_predict is not None:
            payload["options"]["num_predict"] = num_predict
        request = urllib.request.Request(
            self.settings.base_url.rstrip("/") + "/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data.get("response") or data.get("thinking") or "")

    def embed(self, text: str) -> list[float]:
        """Create one embedding with Ollama.

        Newer Ollama versions expose `/api/embed`; older deployments may only
        expose `/api/embeddings`, so keep a fallback for local compatibility.
        """

        try:
            return self._embed_v2(text)
        except Exception:
            return self._embed_legacy(text)

    def _chat_openai_compatible(self, messages: list[dict[str, str]]) -> str:
        payload = {
            "model": self.settings.model_name,
            "messages": messages,
            "temperature": self.settings.temperature,
            "stream": False,
        }
        request = urllib.request.Request(
            self.settings.base_url.rstrip("/") + "/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        return str(data["choices"][0]["message"]["content"])

    def _embed_v2(self, text: str) -> list[float]:
        payload = {
            "model": self.settings.embedding_model_name,
            "input": text,
        }
        request = urllib.request.Request(
            self.settings.base_url.rstrip("/") + "/api/embed",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        embeddings = data.get("embeddings") or []
        if embeddings and isinstance(embeddings[0], list):
            return [float(value) for value in embeddings[0]]
        raise RuntimeError("ollama embed response does not contain embeddings")

    def _embed_legacy(self, text: str) -> list[float]:
        payload = {
            "model": self.settings.embedding_model_name,
            "prompt": text,
        }
        request = urllib.request.Request(
            self.settings.base_url.rstrip("/") + "/api/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.settings.timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
        embedding = data.get("embedding")
        if isinstance(embedding, list):
            return [float(value) for value in embedding]
        raise RuntimeError("ollama embeddings response does not contain embedding")
