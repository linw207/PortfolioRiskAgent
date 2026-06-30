from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ApiRequestContext:
    user_id: str = "user_demo"


def body_or_empty(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload or {}
