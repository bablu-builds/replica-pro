import os
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from rmao.core.executor import Orchestrator

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "default-secret-change-me")

@router.post("/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """Trigger orchestrator via GitHub webhook (push event)."""
    token = request.headers.get("X-Orchestrator-Token")
    if token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    payload = await request.json()
    commits = payload.get("commits", [])
    query = None
    
    for commit in commits:
        message = commit.get("message", "")
        if "[RMAO]" in message:
            query = message.replace("[RMAO]", "").strip()
            break

    if not query:
        raise HTTPException(status_code=400, detail="No [RMAO] directive found in commit")

    background_tasks.add_task(run_orchestrator_background, query)
    return {"status": "accepted", "message": "Orchestration started", "query": query}


async def run_orchestrator_background(query: str):
    orch = Orchestrator()
    try:
        result = await orch.run(query)
        print(f"✅ Background task completed: {result}")
    except Exception as e:
        print(f"❌ Background task failed: {e}")
