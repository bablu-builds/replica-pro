"""Publish successful execution results to GitHub."""
from __future__ import annotations

from ..domain.types import MergeResult, OrchestratorRunSummary, TaskPlan
from .base import GitHubProvider


class GitHubWorkflow:
    """Coordinate per-task branch and pull-request publishing."""

    def __init__(
        self,
        provider: GitHubProvider,
        base_branch: str = "main",
        create_pull_requests: bool = True,
        merge_pull_requests: bool = False,
    ) -> None:
        self.provider = provider
        self.base_branch = base_branch
        self.create_pull_requests = create_pull_requests
        self.merge_pull_requests = merge_pull_requests

    async def publish(
        self,
        run_id: str,
        plan: TaskPlan,
        summary: OrchestratorRunSummary,
    ) -> dict[str, MergeResult]:
        results: dict[str, MergeResult] = {}
        for task in plan.tasks:
            execution = summary.task_results.get(task.task_id)
            if not execution or not execution.success:
                continue
            try:
                results[task.task_id] = await self.provider.publish_task(
                    run_id=run_id,
                    task=task,
                    artifacts=execution.artifacts,
                    base_branch=self.base_branch,
                    create_pull_request=self.create_pull_requests,
                    merge_pull_request=self.merge_pull_requests,
                )
            except Exception as error:
                results[task.task_id] = MergeResult(
                    task_id=task.task_id,
                    success=False,
                    branch_name=f"rmao/{run_id}/{task.branch_slug}",
                    error_message=str(error),
                )
        return results