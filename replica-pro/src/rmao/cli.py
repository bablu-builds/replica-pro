import subprocess
import sys
import os
from pathlib import Path
import click

@click.group()
def cli():
    """Replica-Pro Orchestrator CLI"""
    pass

@cli.command()
@click.argument("query")
@click.option("--tasks", default=4, help="Number of parallel tasks")
def run(query, tasks):
    """Run full orchestration"""
    import asyncio
    from rmao.core.executor import Orchestrator
    asyncio.run(Orchestrator().run(query))

@cli.command()
@click.argument("query")
@click.option("--tasks", default=4, help="Number of parallel tasks")
def plan(query, tasks):
    """Only plan tasks (dry run)"""
    from rmao.core.task_planner import TaskPlanner
    from rmao.llm_manager import LLMManager
    planner = TaskPlanner(LLMManager())
    result = planner.plan(query)
    print(result)

@cli.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", default=8000)
def serve(host, port):
    """Start HTTP API server"""
    import uvicorn
    uvicorn.run("rmao.main:app", host=host, port=port, reload=True)

@cli.command()
def ui():
    """Start Streamlit Web Dashboard"""
    dashboard_path = Path(__file__).parent / "ui" / "dashboard.py"
    if not dashboard_path.exists():
        print("❌ Dashboard not found at:", dashboard_path)
        return
    subprocess.run(["streamlit", "run", str(dashboard_path), "--server.port", "8501"])

if __name__ == "__main__":
    cli()
