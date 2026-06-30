from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/schedules", tags=["schedule"])


@router.post("")
def create_schedule(request: Request, payload: dict) -> dict:
    try:
        return api_ok(
            request.app.state.container.schedule_service.create_job(
                user_id=payload.get("user_id", "user_demo"),
                payload=payload,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_schedules(request: Request, user_id: str = "user_demo") -> dict:
    return api_ok(request.app.state.container.schedule_service.list_jobs(user_id))


@router.post("/run-enabled")
def run_enabled_schedules(request: Request, payload: dict | None = None) -> dict:
    payload = payload or {}
    return api_ok(request.app.state.container.scheduled_task_executor.run_enabled_jobs(payload.get("user_id")))


@router.post("/recover")
def recover_tasks(request: Request, payload: dict | None = None) -> dict:
    payload = payload or {}
    return api_ok(request.app.state.container.scheduled_task_executor.recover_unfinished_tasks(payload.get("user_id")))


@router.get("/{job_id}")
def get_schedule(request: Request, job_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.schedule_service.get_job(job_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{job_id}")
def update_schedule(request: Request, job_id: str, payload: dict) -> dict:
    try:
        return api_ok(request.app.state.container.schedule_service.update_job(job_id, payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{job_id}")
def delete_schedule(request: Request, job_id: str) -> dict:
    try:
        return api_ok({"deleted": request.app.state.container.schedule_service.delete_job(job_id)})
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{job_id}/run")
def run_schedule(request: Request, job_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.scheduled_task_executor.run_job(job_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
