from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/portfolios", tags=["portfolio"])


@router.post("")
def create_portfolio(request: Request, payload: dict) -> dict:
    try:
        portfolio = request.app.state.container.portfolio_service.create_portfolio(
            user_id=payload.get("user_id", "user_demo"),
            name=payload.get("name", "默认持仓组合"),
            holdings_payload=payload.get("holdings", []),
        )
        return api_ok(portfolio)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_portfolios(request: Request, user_id: str = "user_demo") -> dict:
    return api_ok(request.app.state.container.portfolio_service.list_portfolios(user_id))


@router.get("/{portfolio_id}")
def get_portfolio(request: Request, portfolio_id: str) -> dict:
    try:
        return api_ok(request.app.state.container.portfolio_service.get_portfolio(portfolio_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/upload")
async def upload_portfolio(request: Request, file: UploadFile = File(...), user_id: str = "user_demo") -> dict:
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Day1-2 当前只接通 CSV，Excel 解析放到后续迭代。")
    result = request.app.state.container.portfolio_service.import_csv(user_id, file.filename, await file.read())
    return api_ok(result)
