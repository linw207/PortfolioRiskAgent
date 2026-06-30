from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/infra", tags=["infra"])


@router.get("/redis/tasks/{task_id}/status")
def get_redis_task_status(request: Request, task_id: str) -> dict:
    return api_ok(request.app.state.container.redis_runtime_service.get_task_status(task_id))


@router.post("/redis/analysis-queue/pop")
def pop_analysis_queue(request: Request) -> dict:
    return api_ok({"task_id": request.app.state.container.redis_runtime_service.pop_analysis_task()})


@router.get("/redis/analysis-queue/size")
def analysis_queue_size(request: Request) -> dict:
    return api_ok({"size": request.app.state.container.redis_runtime_service.analysis_queue_size()})


@router.post("/vector/announcements/upsert")
def upsert_announcement_chunks(request: Request, payload: dict) -> dict:
    return api_ok(request.app.state.container.vector_memory_service.upsert_announcement_chunks(payload.get("chunks", [])))


@router.post("/vector/announcements/search")
def search_announcement_chunks(request: Request, payload: dict) -> dict:
    return api_ok(
        request.app.state.container.vector_memory_service.search_announcement_chunks(
            query=payload["query"],
            symbol=payload.get("symbol"),
            limit=int(payload.get("limit", 5)),
        )
    )


@router.post("/vector/memory/upsert")
def upsert_agent_memory(request: Request, payload: dict) -> dict:
    return api_ok(request.app.state.container.vector_memory_service.upsert_agent_memory(payload.get("memories", [])))


@router.post("/vector/memory/search")
def search_agent_memory(request: Request, payload: dict) -> dict:
    return api_ok(
        request.app.state.container.vector_memory_service.search_agent_memory(
            query=payload["query"],
            user_id=payload.get("user_id"),
            symbol=payload.get("symbol"),
            limit=int(payload.get("limit", 5)),
        )
    )
