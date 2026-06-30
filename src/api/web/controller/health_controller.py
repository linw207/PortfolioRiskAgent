from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.web.serializer import api_ok


router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request) -> dict:
    return api_ok(request.app.state.container.health_service.health())
