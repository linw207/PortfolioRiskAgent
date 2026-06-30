from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any

from src.domain.entity import ToolCallRecord
from src.domain.tool import MCPToolResult, MCPToolSpec
from src.infra.repo.mem import MemUnitOfWork


class MCPToolRegistry:
    def __init__(self, uow: MemUnitOfWork) -> None:
        self.uow = uow
        self._tools: dict[str, MCPToolSpec] = {}

    def register(self, spec: MCPToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"工具已注册: {spec.name}")
        self._tools[spec.name] = spec

    def get(self, name: str) -> MCPToolSpec | None:
        return self._tools.get(name)

    def list_specs(self) -> list[dict[str, Any]]:
        return [spec.public_dict() for spec in self._tools.values()]

    def call(self, name: str, arguments: dict[str, Any], task_id: str = "") -> MCPToolResult:
        spec = self._tools.get(name)
        if spec is None:
            result = MCPToolResult(
                success=False,
                data={},
                source="tool_registry",
                error_code="TOOL_NOT_ALLOWED",
                error_message=f"工具未注册或不在白名单中: {name}",
            )
            self._record(task_id, name, arguments, result)
            return result

        validation_error = self._validate_arguments(spec, arguments)
        if validation_error:
            result = MCPToolResult(
                success=False,
                data={"schema": spec.input_schema},
                source=spec.data_source,
                error_code="INVALID_ARGUMENTS",
                error_message=validation_error,
            )
            self._record(task_id, name, arguments, result)
            return result

        try:
            result = spec.handler(arguments)
        except Exception as exc:  # noqa: BLE001 - tool boundary must not crash Agent runtime
            result = MCPToolResult(
                success=False,
                data={},
                source=spec.data_source,
                error_code="TOOL_EXECUTION_ERROR",
                error_message=str(exc),
            )
        self._record(task_id, name, arguments, result)
        return result

    def _validate_arguments(self, spec: MCPToolSpec, arguments: dict[str, Any]) -> str:
        required = spec.input_schema.get("required", [])
        missing = [key for key in required if key not in arguments]
        if missing:
            return f"缺少必填参数: {', '.join(missing)}"
        properties = spec.input_schema.get("properties", {})
        for key in arguments:
            if key not in properties:
                return f"未知参数: {key}"
        for key, rule in properties.items():
            if key not in arguments:
                continue
            expected = rule.get("type")
            value = arguments[key]
            if expected == "string" and not isinstance(value, str):
                return f"{key} 必须是字符串"
            if expected == "number" and not isinstance(value, (int, float)):
                return f"{key} 必须是数字"
            if expected == "integer" and not isinstance(value, int):
                return f"{key} 必须是整数"
            if expected == "array" and not isinstance(value, list):
                return f"{key} 必须是数组"
            if expected == "object" and not isinstance(value, dict) and not is_dataclass(value):
                return f"{key} 必须是对象"
        return ""

    def _record(self, task_id: str, tool_name: str, arguments: dict[str, Any], result: MCPToolResult) -> None:
        preview = str(result.data)
        if len(preview) > 500:
            preview = preview[:497] + "..."
        self.uow.tool_calls.save(
            ToolCallRecord(
                task_id=task_id,
                tool_name=tool_name,
                arguments=arguments,
                success=result.success,
                source=result.source,
                error_code=result.error_code,
                error_message=result.error_message,
                result_summary=preview,
            )
        )
