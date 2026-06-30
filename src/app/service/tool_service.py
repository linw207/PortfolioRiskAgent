from __future__ import annotations

from typing import Any

from src.infra.adapter.mcp import MCPToolRegistry, parse_json_action


class ToolService:
    def __init__(self, registry: MCPToolRegistry) -> None:
        self.registry = registry

    def list_tools(self) -> list[dict[str, Any]]:
        return self.registry.list_specs()

    def call_tool(self, tool_name: str, arguments: dict[str, Any], task_id: str = "") -> dict[str, Any]:
        return self.registry.call(tool_name, arguments, task_id=task_id).to_dict()

    def call_json_action(self, action_text: str, task_id: str = "") -> dict[str, Any]:
        action = parse_json_action(action_text)
        result = self.registry.call(action["动作"], action["参数"], task_id=task_id)
        return {"thought": action["思考"], "action": action["动作"], "result": result.to_dict()}
