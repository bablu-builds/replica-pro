"""Dependency-free JSON HTTP API for the orchestrator."""
from __future__ import annotations

import asyncio
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any

from ..config.models import RMAOConfig
from ..orchestration.orchestrator import Orchestrator, build_orchestrator


class RMAOService:
    """Small service layer shared by HTTP handlers and tests."""

    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator
        self._lock = Lock()

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


class _Handler(BaseHTTPRequestHandler):
    service: RMAOService

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._send(200, {"status": "ok", "service": "rmao"})
            return
        if self.path.startswith("/v1/runs/"):
            run_id = self.path.removeprefix("/v1/runs/")
            result = self.service.get_run(run_id)
            self._send(200 if result else 404, result or {"error": "run not found"})
            return
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path.startswith("/v1/runs/") and self.path.endswith("/cancel"):
            run_id = self.path.removeprefix("/v1/runs/").removesuffix("/cancel")
            cancelled = self.service.cancel(run_id)
            self._send(
                202 if cancelled else 404,
                {"run_id": run_id, "cancel_requested": cancelled},
            )
            return
        if self.path not in {"/v1/plan", "/v1/runs"}:
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1_000_000:
                raise ValueError("request body is too large")
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            if self.path == "/v1/plan":
                result = asyncio.run(self.service.plan(payload))
            else:
                result = asyncio.run(self.service.run(payload))
            self._send(200, result)
        except ValueError as error:
            self._send(400, {"error": str(error)})
        except Exception as error:
            self._send(500, {"error": str(error)})


def serve(
    config: RMAOConfig,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Start the HTTP API until interrupted."""
    service = RMAOService(build_orchestrator(config))

    class Handler(_Handler):
        pass

    Handler.service = service
    with ThreadingHTTPServer((host, port), Handler) as server:
        server.serve_forever()