from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any


def calculate_portfolio_risk(holdings: list[dict[str, Any]], quotes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    positions = []
    industry_values: dict[str, Decimal] = defaultdict(Decimal)
    total_market_value = Decimal("0")
    total_cost = Decimal("0")

    for holding in holdings:
        symbol = holding["symbol"]
        shares = Decimal(str(holding["shares"]))
        cost_price = Decimal(str(holding["cost_price"]))
        quote = quotes.get(symbol, {})
        price = quote.get("price")
        industry = quote.get("industry") or "数据不足"
        cost_value = shares * cost_price
        market_value = Decimal("0") if price is None else shares * Decimal(str(price))
        pnl = market_value - cost_value if price is not None else None
        pnl_pct = pnl / cost_value if pnl is not None and cost_value > 0 else None
        total_cost += cost_value
        total_market_value += market_value
        industry_values[industry] += market_value
        positions.append(
            {
                "symbol": symbol,
                "name": holding.get("name") or quote.get("name") or symbol,
                "shares": float(shares),
                "cost_price": float(cost_price),
                "current_price": float(price) if price is not None else None,
                "market_value": float(market_value),
                "cost_value": float(cost_value),
                "pnl": float(pnl) if pnl is not None else None,
                "pnl_pct": float(pnl_pct) if pnl_pct is not None else None,
                "industry": industry,
                "quote_source": quote.get("source", "missing"),
            }
        )

    for item in positions:
        item["weight"] = item["market_value"] / float(total_market_value) if total_market_value else 0

    positions.sort(key=lambda item: item["market_value"], reverse=True)
    risk_flags = []
    for item in positions:
        if item["weight"] >= 0.35:
            risk_flags.append({"symbol": item["symbol"], "type": "position_concentration", "severity": "high"})
        if item["pnl_pct"] is not None and item["pnl_pct"] <= -0.1:
            risk_flags.append({"symbol": item["symbol"], "type": "loss_warning", "severity": "medium"})

    return {
        "total_market_value": float(total_market_value),
        "total_cost": float(total_cost),
        "total_pnl": float(total_market_value - total_cost),
        "total_pnl_pct": float((total_market_value - total_cost) / total_cost) if total_cost else None,
        "highest_position_weight": positions[0]["weight"] if positions else 0,
        "top3_weight": sum(item["weight"] for item in positions[:3]),
        "industry_concentration": {
            industry: float(value / total_market_value) if total_market_value else 0
            for industry, value in industry_values.items()
        },
        "positions": positions,
        "risk_flags": risk_flags,
        "formulas": {
            "market_value": "shares * current_price",
            "pnl_pct": "(market_value - cost_value) / cost_value",
            "position_weight": "position_market_value / portfolio_market_value",
        },
    }
