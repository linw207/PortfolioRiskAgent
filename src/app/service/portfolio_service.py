from __future__ import annotations

import csv
import io
from typing import Any

from src.app.service.validation import normalize_symbol, optional_ratio, to_decimal
from src.domain.entity import Holding, Portfolio
from src.infra.repo.mem import MemUnitOfWork


FIELD_ALIASES = {
    "symbol": {"symbol", "股票代码", "代码", "证券代码"},
    "shares": {"shares", "持仓数量", "数量", "股数"},
    "cost_price": {"cost_price", "成本价", "买入价", "持仓成本"},
    "name": {"name", "股票名称", "名称", "证券名称"},
    "buy_reason": {"buy_reason", "买入理由", "理由", "交易理由"},
    "buy_date": {"buy_date", "买入日期", "交易日期"},
    "max_loss_limit": {"max_loss_limit", "最大亏损线", "止损线"},
    "position_limit": {"position_limit", "单股仓位上限"},
    "industry_limit": {"industry_limit", "行业仓位上限"},
}


class PortfolioService:
    def __init__(self, uow: MemUnitOfWork) -> None:
        self.uow = uow

    def create_portfolio(self, user_id: str, name: str, holdings_payload: list[dict[str, Any]]) -> Portfolio:
        holdings = [self._build_holding(item) for item in holdings_payload]
        if not holdings:
            raise ValueError("持仓数量必须大于 0")
        portfolio = Portfolio(user_id=user_id, name=name or "默认持仓组合", holdings=holdings)
        return self.uow.portfolios.save(portfolio)

    def import_csv(self, user_id: str, filename: str, content: bytes) -> dict[str, Any]:
        text = _decode_text(content)
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return {"portfolio": None, "success_count": 0, "failed_count": 0, "errors": ["文件中未发现持仓数据，请检查后重新上传"]}

        field_map = {field: _canonical_field(field) for field in reader.fieldnames}
        present = {value for value in field_map.values() if value}
        missing = sorted({"symbol", "shares", "cost_price"} - present)
        if missing:
            return {"portfolio": None, "success_count": 0, "failed_count": 0, "errors": [f"必填字段缺失: {', '.join(missing)}"]}

        holdings = []
        errors = []
        for row_number, row in enumerate(reader, start=2):
            data = {target: row.get(source, "") for source, target in field_map.items() if target}
            try:
                holdings.append(self._build_holding(data))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"第 {row_number} 行: {exc}")

        portfolio = None
        if holdings:
            portfolio = self.uow.portfolios.save(Portfolio(user_id=user_id, name=filename, holdings=holdings))
        return {
            "portfolio": portfolio,
            "success_count": len(holdings),
            "failed_count": len(errors),
            "errors": errors,
        }

    def get_portfolio(self, portfolio_id: str) -> Portfolio:
        portfolio = self.uow.portfolios.get(portfolio_id)
        if portfolio is None:
            raise ValueError("持仓组合不存在")
        return portfolio

    def list_portfolios(self, user_id: str) -> list[Portfolio]:
        return self.uow.portfolios.list_by_user(user_id)

    def _build_holding(self, payload: dict[str, Any]) -> Holding:
        return Holding(
            symbol=normalize_symbol(payload["symbol"]),
            shares=to_decimal(payload["shares"], "持仓数量"),
            cost_price=to_decimal(payload["cost_price"], "成本价"),
            name=str(payload.get("name", ""))[:50],
            buy_reason=str(payload.get("buy_reason", ""))[:500],
            buy_date=str(payload.get("buy_date", "")),
            max_loss_limit=optional_ratio(payload.get("max_loss_limit"), "最大亏损线"),
            position_limit=optional_ratio(payload.get("position_limit"), "单股仓位上限"),
            industry_limit=optional_ratio(payload.get("industry_limit"), "行业仓位上限"),
        )


def _canonical_field(name: str) -> str | None:
    for canonical, aliases in FIELD_ALIASES.items():
        if name.strip() in aliases:
            return canonical
    return None


def _decode_text(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("gb18030")
