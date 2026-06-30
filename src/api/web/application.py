from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from log.logging_config import setup_logging
from src.api.web.controller import (
    evaluation_controller,
    health_controller,
    infra_controller,
    model_controller,
    notification_controller,
    portfolio_controller,
    report_controller,
    schedule_controller,
    task_controller,
    tool_controller,
    trade_journal_controller,
    watch_controller,
)
from src.factory import create_container


def create_app() -> FastAPI:
    setup_logging()
    container = create_container()
    app = FastAPI(
        title="PortfolioRiskAgent",
        version="0.1.0-day13",
        description="DDD-style backend for a portfolio risk Agent. Day13 adds reproducible evaluation suites.",
    )
    app.state.container = container
    app.include_router(health_controller.router)
    app.include_router(infra_controller.router)
    app.include_router(model_controller.router)
    app.include_router(portfolio_controller.router)
    app.include_router(watch_controller.router)
    app.include_router(trade_journal_controller.router)
    app.include_router(task_controller.router)
    app.include_router(tool_controller.router)
    app.include_router(notification_controller.router)
    app.include_router(schedule_controller.router)
    app.include_router(report_controller.router)
    app.include_router(evaluation_controller.router)
    static_dir = Path(__file__).resolve().parents[2] / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/app", include_in_schema=False)
        def demo_app() -> FileResponse:
            return FileResponse(static_dir / "app.html")

    return app
