from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/trade-journals", tags=["trade-journal"])


@router.post("")
def add_trade_journal(request: Request, payload: dict) -> dict:
    try:
        return api_ok(
            request.app.state.container.trade_journal_service.add_journal(
                user_id=payload.get("user_id", "user_demo"),
                payload=payload,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_trade_journals(request: Request, user_id: str = "user_demo", symbol: str | None = None) -> dict:
    try:
        return api_ok(request.app.state.container.trade_journal_service.list_journals(user_id, symbol))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
