from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, TypeVar


T = TypeVar("T")


def encode(value: Any) -> Any:
    if is_dataclass(value):
        return {key: encode(item) for key, item in asdict(value).items()}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [encode(item) for item in value]
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    return value


def decode_decimal(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    return Decimal(str(value))
