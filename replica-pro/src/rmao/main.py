"""FastAPI application entry point."""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from rmao.api.webhooks import router
from rmao.config import load_config
from rmao.core.execute import build_orchestrator
from rmao.middleware import RateLimitMiddleware

settings = load_config()
orchestrator = build_orchestrator(settings)

app = FastAPI(
    title="Replica-Pro Orchestrator",
    description="Multi-agent orchestrator for Replit + LLM + GitHub",
    version="1.0.0"
)

# CORS middleware (optional)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)
app.state.orchestrator = orchestrator
app.include_router(router, prefix="/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "mode": settings.mode}


@app.post("/v1/run")
async def run_orchestrator(
    query: Annotated[str, Query(min_length=1)],
    tasks: Annotated[int, Query(ge=1, le=16)] = 4,
):
    """Run orchestration and return its complete typed summary."""
    result = await orchestrator.run(query.strip(), task_count=tasks)
    return result.model_dump(mode="json")
