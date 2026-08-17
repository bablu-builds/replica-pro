"""FastAPI service for planning, running, and monitoring RMAO."""

from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request

from ..config.models import RMAOConfig
from ..logging.redaction import setup_logging
from ..middleware import install_middleware, limiter
from ..orchestration.orchestrator import Orchestrator, build_orchestrator
from .webhooks import create_webhook_router


class RMAOService:
    """Small service layer shared by FastAPI handlers and tests."""

    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator

    async def plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = _request_text(payload)
        task_count = _task_count(payload)
        plan = await self.orchestrator.plan(request, task_count)
        return plan.model_dump(mode="json")

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = _request_text(payload)
        task_count = _task_count(payload)
        summary = await self.orchestrator.run(request, task_count)
        return summary.model_dump(mode="json")

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        summary = self.orchestrator.runs.get(run_id)
        return summary.model_dump(mode="json") if summary else None

    def list_runs(self) -> list[dict[str, Any]]:
        return [
            summary.model_dump(mode="json")
            for summary in reversed(list(self.orchestrator.runs.values()))
        ]

    def cancel(self, run_id: str) -> bool:
        return self.orchestrator.cancel(run_id)


def _request_text(payload: dict[str, Any]) -> str:
    request = payload.get("request")
    if not isinstance(request, str) or not request.strip():
        raise ValueError("'request' must be a non-empty string")
    return request.strip()


def _task_count(payload: dict[str, Any]) -> int | None:
    value = payload.get("tasks")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 16:
        raise ValueError("'tasks' must be an integer between 1 and 16")
    return value


def create_app(
    config: RMAOConfig,
    orchestrator: Orchestrator | None = None,
) -> FastAPI:
    """Create a fully configured FastAPI application."""
    service = RMAOService(orchestrator or build_orchestrator(config))
    app = FastAPI(
        title="Replica-Pro Orchestrator",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    setup_logging(config.log_level, config.log_redact_secrets)
    app.state.rmao_service = service
    install_middleware(app)
    app.include_router(create_webhook_router(service.orchestrator))

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "rmao"}

    @app.get("/v1/runs")
    async def list_runs() -> list[dict[str, Any]]:
        return service.list_runs()

    @app.get("/v1/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        result = service.get_run(run_id)
        if result is None:
            raise HTTPException(status_code=404, detail="run not found")
        return result

    @app.post("/v1/plan")
    async def plan(payload: dict[str, Any]) -> dict[str, Any]:
        return await service.plan(payload)

    @app.post("/v1/runs")
    @limiter.limit("10/minute")
    async def run(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        # request is intentionally present for slowapi's key function; bodies
        # are never logged by the request middleware.
        del request
        return await service.run(payload)

    @app.post("/run")
    @limiter.limit("10/minute")
    async def run_alias(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        del request
        return await service.run(payload)

    @app.post("/v1/runs/{run_id}/cancel", status_code=202)
    async def cancel(run_id: str) -> dict[str, Any]:
        cancelled = service.cancel(run_id)
        if not cancelled:
            raise HTTPException(status_code=404, detail="run not found or already finished")
        return {"run_id": run_id, "cancel_requested": True}

    return app


def serve(
    config: RMAOConfig,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Start the FastAPI service until interrupted."""
    uvicorn.run(create_app(config), host=host, port=port, log_config=None)