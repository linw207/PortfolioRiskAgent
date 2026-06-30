from __future__ import annotations

import unittest

from config.settings import MarketDataSettings
from src.app.service.validation import normalize_symbol, symbol_region
from src.infra.external.itick_client import ITickClient
from src.infra.external.market_data_gateway import MarketDataGateway


class FakeITickClient(ITickClient):
    def __init__(self) -> None:
        pass

    def quote(self, symbol: str) -> dict:
        return {
            "symbol": normalize_symbol(symbol),
            "name": "腾讯控股",
            "price": 390.5,
            "previous_close": 388.0,
            "change_pct": 0.0064,
            "volume": 12345,
            "market": "HK",
            "realtime": True,
            "cache_hit": False,
        }

    def status(self) -> dict:
        return {"provider": "iTick", "configured": True}


class RealtimeMarketDataTest(unittest.TestCase):
    def test_normalize_hk_symbol(self) -> None:
        self.assertEqual(normalize_symbol("700"), "00700.HK")
        self.assertEqual(normalize_symbol("00700.HK"), "00700.HK")
        self.assertEqual(normalize_symbol("700.hk"), "00700.HK")
        self.assertEqual(symbol_region("00700.HK"), "HK")

    def test_market_gateway_prefers_itick_for_hk(self) -> None:
        gateway = MarketDataGateway(
            itick_client=FakeITickClient(),
            settings=MarketDataSettings(provider_order=("itick", "sample")),
        )
        quote, source, degraded = gateway.stock_quote("700")
        self.assertEqual(source, "iTick")
        self.assertFalse(degraded)
        self.assertEqual(quote["symbol"], "00700.HK")
        self.assertTrue(quote["realtime"])

    def test_market_gateway_falls_back_to_sample_without_itick_token(self) -> None:
        gateway = MarketDataGateway(settings=MarketDataSettings(provider_order=("itick", "sample"), itick_api_token=""))
        quote, source, degraded = gateway.stock_quote("00700.HK")
        self.assertEqual(source, "local_sample")
        self.assertTrue(degraded)
        self.assertEqual(quote["name"], "腾讯控股")


if __name__ == "__main__":
    unittest.main()
