from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.post("")
def add_watch_item(request: Request, payload: dict) -> dict:
    try:
        return api_ok(
            request.app.state.container.watch_service.add_watch_item(
                user_id=payload.get("user_id", "user_demo"),
                payload=payload,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_watch_items(request: Request, user_id: str = "user_demo") -> dict:
    return api_ok(request.app.state.container.watch_service.list_watch_items(user_id))


@router.delete("/{watch_id}")
def delete_watch_item(request: Request, watch_id: str) -> dict:
    return api_ok({"deleted": request.app.state.container.watch_service.delete_watch_item(watch_id)})
