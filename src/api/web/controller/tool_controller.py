from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("")
def list_tools(request: Request) -> dict:
    return api_ok(request.app.state.container.tool_service.list_tools())


@router.post("/{tool_name}/call")
def call_tool(request: Request, tool_name: str, payload: dict) -> dict:
    arguments = payload.get("arguments", payload)
    task_id = payload.get("task_id", "")
    return api_ok(request.app.state.container.tool_service.call_tool(tool_name, arguments, task_id=task_id))


@router.post("/json-action")
def call_json_action(request: Request, payload: dict) -> dict:
    return api_ok(
        request.app.state.container.tool_service.call_json_action(
            action_text=payload["action_text"],
            task_id=payload.get("task_id", ""),
        )
    )
