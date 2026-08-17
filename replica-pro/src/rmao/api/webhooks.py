import os
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from rmao.core.execute import Orchestrator

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "default-secret-change-me")


@router.post("/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Trigger orchestrator via GitHub webhook (push event)."""
    # Validate signature (simplified)
    token = request.headers.get("X-Orchestrator-Token")
    if token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    payload = await request.json()
    
    # Extract project query from commit message or specific file
    commits = payload.get("commits", [])
    query = None
    for commit in commits:
        message = commit.get("message", "")
        if "[RMAO]" in message:
            query = message.replace("[RMAO]", "").strip()
            break

    if not query:
        raise HTTPException(status_code=400, detail="No [RMAO] directive found in commit")

    # Run in background (don't block webhook response)
    background_tasks.add_task(run_orchestrator_background, query)
    return {"status": "accepted", "message": "Orchestration started", "query": query}


async def run_orchestrator_background(query: str):
    """Background task to avoid timeout."""
    orch = Orchestrator()
    try:
        result = await orch.run(query)
        print(f"✅ Background task completed: {result}")
    except Exception as e:
        print(f"❌ Background task failed: {e}")
