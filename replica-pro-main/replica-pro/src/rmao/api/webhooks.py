"""Inbound GitHub webhook support."""

from __future__ import annotations

import hmac
import json
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Request

from ..orchestration.orchestrator import Orchestrator


load_dotenv()


def create_webhook_router(orchestrator: Orchestrator) -> APIRouter:
    """Build a router bound to one orchestrator instance."""
    router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])

    @router.post("/github", status_code=202)
    async def github_webhook(request: Request) -> dict[str, Any]:
        expected = os.getenv("RMAO_WEBHOOK_TOKEN", "").strip()
        if not expected:
            raise HTTPException(
                status_code=503,
                detail="Webhook authentication is not configured",
            )
        provided = request.headers.get("X-Orchestrator-Token", "")
        if not provided or not hmac.compare_digest(provided, expected):
            raise HTTPException(status_code=401, detail="Invalid orchestrator token")

        try:
            payload = await request.json()
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=400, detail="Webhook body must be valid JSON") from error
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Webhook body must be a JSON object")

        try:
            project_query, task_count = extract_project_request(payload)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        # Keep the request fast. start_run stores a summary immediately and
        # schedules the actual planning/execution on the active event loop.
        run_id = orchestrator.start_run(project_query, task_count)
        return {"accepted": True, "run_id": run_id}

    return router


def extract_project_request(payload: dict[str, Any]) -> tuple[str, int | None]:
    """Extract a user request from common GitHub and custom webhook payloads."""
    config = _config_from_payload(payload)
    query = _first_string(
        config.get("request") if isinstance(config, dict) else None,
        payload.get("project_query"),
        payload.get("request"),
        payload.get("query"),
        _nested_string(payload, ("rmao", "request")),
        _nested_string(payload, ("client_payload", "request")),
        _commit_request(payload),
    )
    if not query:
        raise ValueError(
            "Webhook did not contain a project request; use project_query or a commit message"
        )

    task_count = None
    candidate = config.get("tasks") if isinstance(config, dict) else None
    if candidate is None:
        candidate = payload.get("tasks")
    if candidate is not None:
        if isinstance(candidate, bool) or not isinstance(candidate, int) or not 1 <= candidate <= 16:
            raise ValueError("Webhook tasks must be an integer between 1 and 16")
        task_count = candidate
    return query.strip()[:10_000], task_count


def _config_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    for candidate in (
        payload.get("config"),
        payload.get("rmao_config"),
        _nested_value(payload, ("rmao", "config")),
    ):
        if isinstance(candidate, dict):
            return candidate

    files = payload.get("files")
    if isinstance(files, list):
        for file_entry in files:
            if not isinstance(file_entry, dict):
                continue
            path = file_entry.get("path") or file_entry.get("filename")
            if path != ".rmao/config.json":
                continue
            content = file_entry.get("content")
            if isinstance(content, str):
                try:
                    decoded = json.loads(content)
                except json.JSONDecodeError:
                    return {}
                return decoded if isinstance(decoded, dict) else {}
    return {}


def _commit_request(payload: dict[str, Any]) -> str | None:
    head_commit = payload.get("head_commit")
    if isinstance(head_commit, dict):
        message = head_commit.get("message")
        if isinstance(message, str) and message.strip():
            return _clean_commit_message(message)

    commits = payload.get("commits")
    if isinstance(commits, list):
        for commit in reversed(commits):
            if isinstance(commit, dict) and isinstance(commit.get("message"), str):
                message = commit["message"].strip()
                if message:
                    return _clean_commit_message(message)
    return None


def _clean_commit_message(message: str) -> str:
    first_line = message.strip().splitlines()[0].strip()
    for prefix in ("[rmao]", "rmao:"):
        if first_line.lower().startswith(prefix):
            first_line = first_line[len(prefix) :].strip()
    return first_line


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _nested_value(value: Any, path: tuple[str, ...]) -> Any:
    current = value
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _nested_string(value: Any, path: tuple[str, ...]) -> str | None:
    result = _nested_value(value, path)
    return result if isinstance(result, str) else None


__all__ = ["create_webhook_router", "extract_project_request"]