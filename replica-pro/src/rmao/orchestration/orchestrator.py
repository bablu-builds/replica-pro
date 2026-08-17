"""Composition root for planning, execution, workers, and GitHub publishing."""
from __future__ import annotations

import time
import uuid
import asyncio

from ..config.models import RMAOConfig
from ..domain.types import OrchestratorRunSummary, RunState
from ..executor.parallel import ParallelExecutor
from ..execution.mock import MockExecutionProvider
from ..execution.replit import ReplitExecutionProvider
from ..github.mock import MockGitHubProvider
from ..github.rest import GitHubRestProvider
from ..github.workflow import GitHubWorkflow
from ..llm.factory import LLMFactory
from ..llm.fake_adapter import FakeLLMAdapter
from ..planner.mock import build_mock_plan
from ..planner.planner import TaskPlanner
from ..pool.pool import AgentPool


class Orchestrator:
    """Run one request through the configured RMAO lifecycle."""

    def __init__(
        self,
        planner: TaskPlanner,
        executor: ParallelExecutor,
        github_workflow: GitHubWorkflow | None = None,
        dry_run: bool = False,
    ) -> None:
        self.planner = planner
        self.executor = executor
        self.github_workflow = github_workflow
        self.dry_run = dry_run
        self.runs: dict[str, OrchestratorRunSummary] = {}
        self.cancel_events: dict[str, asyncio.Event] = {}

    async def plan(self, request: str, task_count: int | None = None):
        return await self.planner.plan(request, task_count)

    async def run(
        self,
        request: str,
        task_count: int | None = None,
        cancel_event=None,
    ) -> OrchestratorRunSummary:
        started = time.monotonic()
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        active_cancel_event = cancel_event or asyncio.Event()
        self.cancel_events[run_id] = active_cancel_event
        summary = OrchestratorRunSummary(run_id=run_id, state=RunState.planning)
        self.runs[run_id] = summary
        try:
            summary.plan = await self.planner.plan(request, task_count)
            if self.dry_run:
                summary.state = RunState.planned
                summary.duration_seconds = time.monotonic() - started
                return summary

            summary.state = RunState.executing
            report = await self.executor.execute(
                summary.plan, run_id, active_cancel_event
            )
            summary.task_results = report.results
            if active_cancel_event.is_set():
                summary.cancelled = True
                summary.state = RunState.cancelled
                summary.duration_seconds = time.monotonic() - started
                return summary

            failures = [
                result for result in report.results.values() if not result.success
            ]
            if failures:
                summary.state = RunState.partially_failed
                summary.errors.extend(
                    result.error_message or f"Task {result.task_id} failed"
                    for result in failures
                )
                summary.duration_seconds = time.monotonic() - started
                return summary

            if self.github_workflow:
                summary.merge_results = await self.github_workflow.publish(
                    run_id, summary.plan, summary
                )
                summary.pr_links = [
                    result.pr_url
                    for result in summary.merge_results.values()
                    if result.pr_url
                ]
                merge_failures = [
                    result for result in summary.merge_results.values() if not result.success
                ]
                if merge_failures:
                    summary.state = RunState.completed_with_warnings
                    summary.warnings.extend(
                        result.error_message or f"Merge failed for {result.task_id}"
                        for result in merge_failures
                    )
                else:
                    summary.state = (
                        RunState.merged
                        if self.github_workflow.merge_pull_requests
                        else RunState.ready_for_merge
                    )
            else:
                summary.state = RunState.completed_with_warnings
                summary.warnings.append("No GitHub workflow configured; artifacts were not published.")
            summary.duration_seconds = time.monotonic() - started
            return summary
        except Exception as error:
            summary.state = RunState.execution_failed
            summary.errors.append(str(error))
            summary.duration_seconds = time.monotonic() - started
            return summary
        finally:
            self.cancel_events.pop(run_id, None)

    def cancel(self, run_id: str) -> bool:
        """Request cancellation for an active run."""
        event = self.cancel_events.get(run_id)
        if not event:
            return False
        event.set()
        return True


def build_orchestrator(config: RMAOConfig, task_count: int | None = None) -> Orchestrator:
    """Construct all providers from validated configuration."""
    count = max(1, min(task_count or config.max_tasks, config.max_tasks))
    if config.llm.provider == "fake":
        llm = FakeLLMAdapter(
            model=config.llm.model,
            timeout=config.llm.timeout,
            max_retries=config.llm.max_retries,
            structured_response=build_mock_plan(count),
        )
    else:
        llm = LLMFactory.create(config.llm)
    planner = TaskPlanner(llm)

    if config.execution.provider == "mock":
        execution_provider = MockExecutionProvider(
            delay_ms=config.execution.mock_delay_ms
        )
    else:
        execution_provider = ReplitExecutionProvider()
    pool = AgentPool(config.execution.worker_count, execution_provider.provider_name)
    executor = ParallelExecutor(
        execution_provider,
        pool,
        max_concurrency=config.max_concurrency,
        task_timeout=config.task_timeout,
    )

    if config.mode == "real":
        github_provider = GitHubRestProvider(
            token=config.github.token or "",
            owner=config.github.owner or "",
            repository=config.github.repository or "",
            base_url=config.github.base_url,
            timeout=config.task_timeout,
        )
    else:
        github_provider = MockGitHubProvider(
            owner=config.github.owner or "mock-owner",
            repository=config.github.repository or "mock-repo",
        )
    workflow = GitHubWorkflow(
        github_provider,
        base_branch=config.github.base_branch,
        create_pull_requests=config.github.create_pull_requests,
        merge_pull_requests=config.github.merge_pull_requests,
    )
    return Orchestrator(
        planner=planner,
        executor=executor,
        github_workflow=workflow,
        dry_run=config.mode == "dry_run",
    )