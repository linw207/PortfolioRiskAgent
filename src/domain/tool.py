from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from src.domain.time import now_iso


ToolHandler = Callable[[dict[str, Any]], "MCPToolResult"]


@dataclass(slots=True)
class MCPToolResult:
    success: bool
    data: dict[str, Any]
    source: str
    fetched_at: str = field(default_factory=now_iso)
    error_code: str | None = None
    error_message: str | None = None
    degraded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "source": self.source,
            "fetched_at": self.fetched_at,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "degraded": self.degraded,
        }


@dataclass(slots=True)
class MCPToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    error_codes: dict[str, str]
    data_source: str
    handler: ToolHandler
    mature_tool_hint: str = ""

    def public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "error_codes": self.error_codes,
            "data_source": self.data_source,
            "mature_tool_hint": self.mature_tool_hint,
        }
