"""FastAPI webhook endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from rmao.core.execute import Orchestrator

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Trigger the configured orchestrator from a GitHub webhook."""
    body = await request.body()
    _validate_webhook(request, body)

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from error
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be an object")

    query = _query_from_payload(payload)
    if not query:
        raise HTTPException(status_code=400, detail="No [RMAO] directive found in commit")

    orchestrator = getattr(request.app.state, "orchestrator", None)
    if not isinstance(orchestrator, Orchestrator):
        raise HTTPException(status_code=503, detail="Orchestrator is not configured")

    background_tasks.add_task(run_orchestrator_background, orchestrator, query)
    return {"status": "accepted", "message": "Orchestration started", "query": query}


def _query_from_payload(payload: dict[str, Any]) -> str | None:
    """Extract the first ``[RMAO]`` directive from a push payload."""
    commits = payload.get("commits", [])
    if not isinstance(commits, list):
        return None
    for commit in commits:
        if not isinstance(commit, dict):
            continue
        message = commit.get("message", "")
        if isinstance(message, str) and "[RMAO]" in message:
            query = message.replace("[RMAO]", "", 1).strip()
            if query:
                return query
    return None


def _validate_webhook(request: Request, body: bytes) -> None:
    """Validate a shared token or GitHub's HMAC-SHA256 signature."""
    secret = os.getenv("WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook secret is not configured")

    token = request.headers.get("X-Orchestrator-Token")
    if token and hmac.compare_digest(token, secret):
        return

    signature = request.headers.get("X-Hub-Signature-256")
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    if signature and hmac.compare_digest(signature, expected):
        return

    raise HTTPException(status_code=401, detail="Invalid webhook credentials")


async def run_orchestrator_background(
    orchestrator: Orchestrator, query: str
) -> None:
    """Run a webhook request without blocking the webhook response."""
    try:
        await orchestrator.run(query)
    except Exception as error:
        # BackgroundTasks cannot return an exception to the webhook caller.
        print(f"Background webhook orchestration failed: {error}")
