from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/reports", tags=["report"])


@router.get("/tasks/{task_id}")
def get_report_by_task(request: Request, task_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.report_archive_service.get_by_task(task_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
