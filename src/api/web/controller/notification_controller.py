from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/notification-channels", tags=["notification"])


@router.post("")
def create_channel(request: Request, payload: dict) -> dict:
    try:
        return api_ok(
            request.app.state.container.notification_service.create_channel(
                user_id=payload.get("user_id", "user_demo"),
                payload=payload,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_channels(request: Request, user_id: str = "user_demo") -> dict:
    return api_ok(request.app.state.container.notification_service.list_channels(user_id))


@router.get("/feishu-cli/status")
def feishu_cli_status(request: Request) -> dict:
    return api_ok(request.app.state.container.notification_service.get_cli_status())


@router.post("/{channel_id}/test")
def test_channel(request: Request, channel_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.notification_service.send_test(channel_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/records")
def list_records(request: Request, user_id: str = "user_demo") -> dict:
    return api_ok(request.app.state.container.notification_service.list_records(user_id))


@router.post("/records/{record_id}/send")
def send_record(request: Request, record_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.notification_service.send_record(record_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/records/retry-failed")
def retry_failed(request: Request, payload: dict | None = None) -> dict:
    payload = payload or {}
    return api_ok(request.app.state.container.notification_service.retry_failed(limit=int(payload.get("limit", 20))))
