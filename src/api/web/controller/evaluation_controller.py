from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.web.serializer import api_ok


router = APIRouter(prefix="/evaluations", tags=["evaluation"])


@router.post("/run")
def run_evaluations(request: Request) -> dict:
    return api_ok(request.app.state.container.evaluation_service.run_all())


@router.get("/latest")
def latest_evaluation(request: Request) -> dict:
    return api_ok(request.app.state.container.evaluation_service.latest() or {})


@router.get("/official/status")
def official_status(request: Request) -> dict:
    return api_ok(request.app.state.container.official_benchmark_service.status())


@router.get("/official/gaia/sample")
def official_gaia_sample(request: Request, limit: int = 5, level: int | None = None) -> dict:
    return api_ok(request.app.state.container.official_benchmark_service.load_gaia_sample(limit=limit, level=level))


@router.post("/official/gaia/run")
def official_gaia_run(
    request: Request,
    limit: int = 3,
    level: int | None = 1,
    config: str = "2023_level1",
    split: str = "validation",
) -> dict:
    return api_ok(
        request.app.state.container.official_benchmark_service.run_gaia_evaluation(
            limit=limit,
            level=level,
            config=config,
            split=split,
            save=True,
        )
    )


@router.post("/official/bfcl/{mode}")
def official_bfcl_cli(request: Request, mode: str) -> dict:
    return api_ok(request.app.state.container.official_benchmark_service.run_bfcl_cli(mode=mode))
