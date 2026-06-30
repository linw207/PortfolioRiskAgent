from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/model", tags=["model"])


@router.get("/health")
def model_health(request: Request) -> dict:
    return api_ok(request.app.state.container.agent_runtime_service.model_health())
