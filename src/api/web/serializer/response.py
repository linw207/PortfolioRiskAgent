from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any


def serialize(value: Any) -> Any:
    if is_dataclass(value):
        return {key: serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value


def api_ok(data: Any = None) -> dict[str, Any]:
    return {"success": True, "data": serialize(data), "error": None}


def api_error(message: str, code: str = "BAD_REQUEST") -> dict[str, Any]:
    return {"success": False, "data": None, "error": {"code": code, "message": message}}
