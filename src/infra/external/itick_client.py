from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from config.settings import MarketDataSettings
from src.app.service.validation import normalize_symbol


class ITickClient:
    """iTick REST market-data adapter.

    The free tier is useful for near-real-time HK quotes. This adapter keeps a
    tiny TTL cache to avoid burning quota when multiple tools request the same
    symbol during one Agent run.
    """

    def __init__(self, settings: MarketDataSettings) -> None:
        self.settings = settings
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def available(self) -> bool:
        return bool(self.settings.itick_api_token)

    def quote(self, symbol: str) -> dict[str, Any]:
        normalized = normalize_symbol(symbol)
        if not normalized.endswith(".HK"):
            raise RuntimeError("iTick adapter currently handles HK symbols only")
        if not self.settings.itick_api_token:
            raise RuntimeError("ITICK_API_TOKEN is not configured")

        cached = self._cache.get(normalized)
        now = time.time()
        if cached and now - cached[0] <= self.settings.realtime_cache_ttl_seconds:
            return {**cached[1], "cache_hit": True}

        data = self._request("/stock/tick", {"region": "HK", "code": _hk_itick_code(normalized)})
        quote = _normalize_itick_tick(normalized, data)
        self._cache[normalized] = (now, quote)
        return quote

    def status(self) -> dict[str, Any]:
        return {
            "provider": "iTick",
            "configured": bool(self.settings.itick_api_token),
            "base_url": self.settings.itick_base_url,
            "timeout_seconds": self.settings.itick_timeout_seconds,
            "cache_ttl_seconds": self.settings.realtime_cache_ttl_seconds,
        }

    def _request(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        query = urllib.parse.urlencode(params)
        url = self.settings.itick_base_url.rstrip("/") + path + "?" + query
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "accept": "application/json",
                "token": self.settings.itick_api_token,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.settings.itick_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"iTick request failed: {exc}") from exc
        if payload.get("code") not in {0, "0"}:
            raise RuntimeError(f"iTick returned error: {payload.get('msg') or payload}")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise RuntimeError("iTick response does not contain data object")
        return data


def _hk_itick_code(symbol: str) -> str:
    return str(int(symbol.split(".")[0]))


def _normalize_itick_tick(symbol: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "name": str(data.get("n") or data.get("name") or ""),
        "price": _float(data.get("ld") or data.get("last") or data.get("price")),
        "previous_close": _float(data.get("pc") or data.get("preClose")),
        "change_pct": _ratio(data.get("chp")),
        "change": _float(data.get("ch")),
        "volume": _float(data.get("v")),
        "turnover": _float(data.get("tu") or data.get("amount")),
        "timestamp_ms": _int(data.get("t")),
        "raw_symbol": str(data.get("s") or ""),
        "market": "HK",
        "realtime": True,
        "cache_hit": False,
    }


def _float(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    if value in (None, "", "-"):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _ratio(value: Any) -> float | None:
    parsed = _float(value)
    if parsed is None:
        return None
    return parsed / 100 if abs(parsed) > 1 else parsed
