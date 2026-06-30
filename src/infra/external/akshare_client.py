from __future__ import annotations

from typing import Any

from src.app.service.validation import normalize_symbol


class AKShareClient:
    """Optional mature data-source adapter.

    AKShare is used when installed and reachable. All methods return normalized
    dictionaries and raise RuntimeError on dependency/API failure so callers can
    fall back to cache/sample data without inventing market data.
    """

    def __init__(self) -> None:
        self._ak: Any | None = None

    def _module(self) -> Any:
        if self._ak is None:
            try:
                import akshare as ak
            except ImportError as exc:
                raise RuntimeError("akshare is not installed") from exc
            self._ak = ak
        return self._ak

    def get_stock_quote(self, symbol: str) -> dict[str, Any]:
        ak = self._module()
        normalized = normalize_symbol(symbol)
        code = normalized.split(".")[0]
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            raise RuntimeError("AKShare stock_zh_a_spot_em returned empty data")
        row = df[df["代码"].astype(str) == code]
        if row.empty:
            raise RuntimeError(f"AKShare quote missing for {normalized}")
        item = row.iloc[0].to_dict()
        return {
            "symbol": normalized,
            "name": str(item.get("名称", "")),
            "price": _float(item.get("最新价")),
            "previous_close": _float(item.get("昨收")),
            "change_pct": _float(item.get("涨跌幅")) / 100 if item.get("涨跌幅") is not None else None,
            "turnover_rate": _float(item.get("换手率")) / 100 if item.get("换手率") is not None else None,
            "volume": _float(item.get("成交量")),
            "industry": "",
        }

    def get_index_quote(self, symbol: str) -> dict[str, Any]:
        ak = self._module()
        code = symbol.split(".")[0]
        df = ak.stock_zh_index_spot_em()
        if df is None or df.empty:
            raise RuntimeError("AKShare stock_zh_index_spot_em returned empty data")
        row = df[df["代码"].astype(str) == code]
        if row.empty:
            raise RuntimeError(f"AKShare index quote missing for {symbol}")
        item = row.iloc[0].to_dict()
        return {
            "symbol": symbol,
            "name": str(item.get("名称", "")),
            "price": _float(item.get("最新价")),
            "change_pct": _float(item.get("涨跌幅")) / 100 if item.get("涨跌幅") is not None else None,
        }

    def search_announcements(self, symbol: str, limit: int = 10) -> list[dict[str, Any]]:
        ak = self._module()
        normalized = normalize_symbol(symbol)
        code = normalized.split(".")[0]
        if not hasattr(ak, "stock_notice_report"):
            raise RuntimeError("AKShare stock_notice_report is unavailable in this installed version")
        df = ak.stock_notice_report(symbol="全部")
        if df is None or df.empty:
            raise RuntimeError("AKShare stock_notice_report returned empty data")
        rows = df[df.astype(str).apply(lambda row: code in " ".join(row.values), axis=1)].head(limit)
        announcements = []
        for _, row in rows.iterrows():
            item = row.to_dict()
            announcements.append(
                {
                    "symbol": normalized,
                    "title": str(item.get("公告标题") or item.get("标题") or ""),
                    "published_at": str(item.get("公告日期") or item.get("日期") or ""),
                    "source": "AKShare",
                    "url": str(item.get("公告链接") or item.get("链接") or ""),
                    "content": str(item.get("公告标题") or item.get("标题") or ""),
                }
            )
        return announcements


def _float(value: Any) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
