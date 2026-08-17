"""Command-line entry point for the orchestrator's planning workflow."""
from __future__ import annotations

import argparse
import asyncio

from ..config import load_config, validate_config
from ..llm.fake_adapter import FakeLLMAdapter
from ..planner.planner import TaskPlanner


def _demo_response(task_count: int) -> dict[str, object]:
    tasks = [
        {
            "task_id": f"task-{index}",
            "name": f"Implementation task {index}",
            "description": f"Implement the next independent part of the request.",
            "responsibilities": ["Implement and verify the assigned scope"],
            "dependencies": [],
            "technology_constraints": [],
            "expected_output_files": [],
            "port": None,
            "branch_slug": f"task-{index}",
            "acceptance_criteria": ["The assigned scope is implemented and verified"],
        }
        for index in range(1, task_count + 1)
    ]
    return {
        "tasks": tasks,
        "summary": "Mock plan generated successfully.",
    }


async def _run_plan(request: str, task_count: int) -> str:
    config = load_config()
    validate_config(config)
    adapter = FakeLLMAdapter(
        model="mock-model",
        structured_response=_demo_response(task_count),
    )
    plan = await TaskPlanner(adapter).plan(request, task_count)
    return TaskPlanner(adapter).summarize(plan)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="rmao",
        description="Replit Multi-Agent Orchestrator",
    )
    parser.add_argument(
        "request",
        nargs="?",
        default="Build a small project",
        help="Project request to decompose into parallel tasks",
    )
    parser.add_argument(
        "--tasks",
        type=int,
        default=4,
        help="Number of tasks to generate (1-16)",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.tasks <= 16:
        parser.error("--tasks must be between 1 and 16")
    print(asyncio.run(_run_plan(args.request, args.tasks)))


if __name__ == "__main__":
    main()