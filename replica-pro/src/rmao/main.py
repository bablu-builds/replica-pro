from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import our modules
from rmao.api.webhooks import router as webhooks_router
from rmao.middleware import RateLimitMiddleware
from rmao.core.executor import Orchestrator
from rmao.config import settings

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

# ✅ Add Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware)

# ✅ Register Webhooks Router
app.include_router(webhooks_router, prefix="/v1")

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "mode": settings.RMAO_MODE}

# Run endpoint
@app.post("/v1/run")
async def run_orchestrator(query: str, tasks: int = 4):
    orch = Orchestrator()
    result = await orch.run(query)
    return {"status": "success", "repo_url": result}
