from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import Any


def normalize_symbol(symbol: str) -> str:
    raw = str(symbol).strip().upper()
    if re.fullmatch(r"\d{6}", raw):
        suffix = "SH" if raw.startswith(("6", "9")) else "SZ"
        return f"{raw}.{suffix}"
    if re.fullmatch(r"\d{6}\.(SH|SZ)", raw):
        return raw
    if re.fullmatch(r"\d{1,5}", raw):
        return f"{raw.zfill(5)}.HK"
    if re.fullmatch(r"\d{1,5}\.HK", raw):
        code = raw.split(".")[0].zfill(5)
        return f"{code}.HK"
    raise ValueError(f"仅支持 A 股和港股代码，无法识别: {symbol}")


def symbol_region(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    if normalized.endswith(".HK"):
        return "HK"
    if normalized.endswith((".SH", ".SZ")):
        return "CN"
    raise ValueError(f"无法识别市场区域: {symbol}")


def to_decimal(value: Any, field_name: str, positive: bool = True) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"{field_name} 必须是数字") from exc
    if positive and parsed <= 0:
        raise ValueError(f"{field_name} 必须为正数")
    return parsed


def optional_ratio(value: Any, field_name: str) -> Decimal | None:
    if value in (None, ""):
        return None
    parsed = to_decimal(value, field_name, positive=False)
    if parsed < 0 or parsed > 1:
        raise ValueError(f"{field_name} 必须是 0 到 1 的小数")
    return parsed


def parse_date(value: str, field_name: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} 必须是 YYYY-MM-DD 日期") from exc
    if parsed > date.today():
        raise ValueError(f"{field_name} 不得晚于当前日期")
    return parsed
