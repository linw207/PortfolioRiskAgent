from __future__ import annotations

from typing import Any

from config.settings import MarketDataSettings
from src.app.service.validation import normalize_symbol
from src.infra.external.akshare_client import AKShareClient
from src.infra.external.itick_client import ITickClient
from src.infra.external.sample_market_data import (
    SAMPLE_ANNOUNCEMENTS,
    SAMPLE_FINANCIALS,
    SAMPLE_INDEX_QUOTES,
    SAMPLE_QUOTES,
)


class MarketDataGateway:
    def __init__(
        self,
        akshare_client: AKShareClient | None = None,
        itick_client: ITickClient | None = None,
        settings: MarketDataSettings | None = None,
    ) -> None:
        self.settings = settings or MarketDataSettings()
        self.akshare = akshare_client or AKShareClient()
        self.itick = itick_client or ITickClient(self.settings)

    def stock_quote(self, symbol: str) -> tuple[dict[str, Any], str, bool]:
        normalized = normalize_symbol(symbol)
        errors = []
        for provider in self.settings.provider_order:
            if provider == "itick":
                try:
                    data = self.itick.quote(normalized)
                    return data, "iTick", False
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"iTick: {exc}")
            elif provider == "akshare":
                try:
                    data = self.akshare.get_stock_quote(normalized)
                    return {**data, "realtime": True}, "AKShare", False
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"AKShare: {exc}")
            elif provider == "sample":
                sample = SAMPLE_QUOTES.get(normalized)
                if sample:
                    return {**sample, "symbol": normalized}, "local_sample", True
        sample = SAMPLE_QUOTES.get(normalized)
        if sample:
            return {**sample, "symbol": normalized, "provider_errors": errors}, "local_sample", True
        raise RuntimeError("; ".join(errors) or f"quote missing for {normalized}")

    def status(self) -> dict[str, Any]:
        return {
            "provider_order": list(self.settings.provider_order),
            "itick": self.itick.status(),
        }

    def index_quote(self, symbol: str = "000300.SH") -> tuple[dict[str, Any], str, bool]:
        try:
            data = self.akshare.get_index_quote(symbol)
            return data, "AKShare", False
        except Exception:
            sample = SAMPLE_INDEX_QUOTES.get(symbol) or SAMPLE_INDEX_QUOTES["000300.SH"]
            return {**sample}, "local_sample", True

    def financial_metrics(self, symbol: str) -> tuple[dict[str, Any], str, bool]:
        normalized = normalize_symbol(symbol)
        # AKShare financial APIs differ across versions. Keep a stable boundary
        # and fall back to curated sample values until Day4 integration is
        # expanded under tests for the installed AKShare version.
        sample = SAMPLE_FINANCIALS.get(normalized)
        if not sample:
            raise RuntimeError(f"financial metrics missing for {normalized}")
        return {"symbol": normalized, **sample}, "local_sample", True

    def announcements(self, symbol: str, limit: int = 10, keywords: list[str] | None = None) -> tuple[list[dict], str, bool]:
        normalized = normalize_symbol(symbol)
        try:
            data = self.akshare.search_announcements(normalized, limit=limit)
            if data:
                return self._filter_keywords(data, keywords), "AKShare", False
        except Exception:
            pass
        sample = [item for item in SAMPLE_ANNOUNCEMENTS if item["symbol"] == normalized]
        return self._filter_keywords(sample, keywords)[:limit], "local_sample", True

    def _filter_keywords(self, items: list[dict], keywords: list[str] | None) -> list[dict]:
        if not keywords:
            return items
        return [
            item
            for item in items
            if any(keyword in item.get("title", "") or keyword in item.get("content", "") for keyword in keywords)
        ]
