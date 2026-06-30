from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/tasks", tags=["task"])


@router.post("")
def create_task(request: Request, payload: dict) -> dict:
    try:
        return api_ok(
            request.app.state.container.task_service.create_task(
                user_id=payload.get("user_id", "user_demo"),
                portfolio_id=payload["portfolio_id"],
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_tasks(request: Request, user_id: str = "user_demo") -> dict:
    return api_ok(request.app.state.container.task_service.list_tasks(user_id))


@router.get("/{task_id}")
def get_task(request: Request, task_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.task_service.get_task(task_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{task_id}/agent-runs")
def list_agent_runs(request: Request, task_id: str) -> dict:
    return api_ok(request.app.state.container.uow.agent_runs.list_by_task(task_id))


@router.get("/{task_id}/tool-calls")
def list_tool_calls(request: Request, task_id: str) -> dict:
    return api_ok(request.app.state.container.uow.tool_calls.list_by_task(task_id))


@router.post("/{task_id}/run-finance-check")
def run_finance_check(request: Request, task_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.task_service.run_finance_check(task_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{task_id}/run-announcement-check")
def run_announcement_check(request: Request, task_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.task_service.run_announcement_check(task_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{task_id}/run-review-check")
def run_review_check(request: Request, task_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.task_service.run_review_check(task_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{task_id}/run-report-check")
def run_report_check(request: Request, task_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.task_service.run_report_check(task_id, notify=True))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
