from __future__ import annotations


SAMPLE_QUOTES = {
    "600519.SH": {
        "symbol": "600519.SH",
        "name": "贵州茅台",
        "price": 1488.0,
        "previous_close": 1502.0,
        "change_pct": -0.0093,
        "industry": "食品饮料",
        "turnover_rate": 0.004,
        "volume": 2150000,
    },
    "000001.SZ": {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "price": 10.45,
        "previous_close": 10.22,
        "change_pct": 0.0225,
        "industry": "银行",
        "turnover_rate": 0.013,
        "volume": 81200000,
    },
    "300750.SZ": {
        "symbol": "300750.SZ",
        "name": "宁德时代",
        "price": 196.8,
        "previous_close": 204.1,
        "change_pct": -0.0358,
        "industry": "电力设备",
        "turnover_rate": 0.021,
        "volume": 23100000,
    },
    "00700.HK": {
        "symbol": "00700.HK",
        "name": "腾讯控股",
        "price": 385.2,
        "previous_close": 382.0,
        "change_pct": 0.0084,
        "industry": "互联网服务",
        "turnover_rate": None,
        "volume": 18320000,
        "market": "HK",
        "realtime": False,
    },
}


SAMPLE_INDEX_QUOTES = {
    "000300.SH": {
        "symbol": "000300.SH",
        "name": "沪深300",
        "price": 3880.0,
        "change_pct": -0.006,
    }
}


SAMPLE_FINANCIALS = {
    "600519.SH": {"pe": 24.8, "pb": 8.2, "roe": 0.31, "revenue_growth": 0.16, "net_profit_growth": 0.15},
    "000001.SZ": {"pe": 4.7, "pb": 0.52, "roe": 0.10, "revenue_growth": -0.04, "net_profit_growth": 0.02},
    "300750.SZ": {"pe": 18.1, "pb": 4.1, "roe": 0.22, "revenue_growth": -0.08, "net_profit_growth": -0.12},
    "00700.HK": {"pe": 22.4, "pb": 4.5, "roe": 0.19, "revenue_growth": 0.08, "net_profit_growth": 0.14},
}


SAMPLE_ANNOUNCEMENTS = [
    {
        "symbol": "300750.SZ",
        "title": "关于控股股东部分股份质押的公告",
        "published_at": "2026-06-05",
        "source": "local_sample_announcement",
        "url": "sample://announcements/300750/pledge",
        "content": "公司控股股东将其持有的部分股份办理质押，本次质押用途为补充流动资金。",
    },
    {
        "symbol": "300750.SZ",
        "title": "关于收到交易所问询函的公告",
        "published_at": "2026-05-21",
        "source": "local_sample_announcement",
        "url": "sample://announcements/300750/inquiry",
        "content": "公司收到交易所问询函，要求说明收入确认、存货跌价准备和海外业务风险。",
    },
    {
        "symbol": "000001.SZ",
        "title": "年度权益分派实施公告",
        "published_at": "2026-06-10",
        "source": "local_sample_announcement",
        "url": "sample://announcements/000001/dividend",
        "content": "公司实施年度权益分派，利润分配方案已经股东大会审议通过。",
    },
]
