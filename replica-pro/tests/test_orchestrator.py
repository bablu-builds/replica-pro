from __future__ import annotations

import pytest

from rmao.api.server import RMAOService
from rmao.config.models import ExecutionConfig, LLMConfig, RMAOConfig
from rmao.domain.types import PlannedTask, TaskPlan
from rmao.execution.mock import MockExecutionProvider
from rmao.executor.parallel import ParallelExecutor
from rmao.github.mock import MockGitHubProvider
from rmao.orchestration.orchestrator import build_orchestrator
from rmao.pool.pool import AgentPool


@pytest.mark.asyncio
async def test_mock_end_to_end_publishes_pull_requests() -> None:
    config = RMAOConfig(
        mode="mock",
        llm=LLMConfig(provider="fake", model="test-model"),
        execution=ExecutionConfig(provider="mock", worker_count=2),
        max_concurrency=2,
        max_tasks=2,
    )
    orchestrator = build_orchestrator(config, task_count=2)
    summary = await orchestrator.run("Build a project", task_count=2)
    assert summary.state.value == "ready_for_merge"
    assert len(summary.task_results) == 2
    assert len(summary.pr_links) == 2


@pytest.mark.asyncio
async def test_parallel_executor_honors_dependencies_and_reports_failure() -> None:
    first = PlannedTask(
        task_id="first",
        name="First",
        description="First task",
        branch_slug="first",
    )
    second = PlannedTask(
        task_id="second",
        name="Second",
        description="Second task",
        dependencies=["first"],
        branch_slug="second",
    )
    provider = MockExecutionProvider(fail_task_ids={"first"})
    executor = ParallelExecutor(provider, AgentPool(2), max_concurrency=2)
    report = await executor.execute(TaskPlan(tasks=[first, second]), "run-test")
    assert not report.results["first"].success
    assert not report.results["second"].success
    assert "dependency" in (report.results["second"].error_message or "")


@pytest.mark.asyncio
async def test_http_service_returns_plan_and_run() -> None:
    config = RMAOConfig(
        mode="mock",
        llm=LLMConfig(provider="fake"),
        execution=ExecutionConfig(provider="mock"),
    )
    service = RMAOService(build_orchestrator(config, task_count=1))
    plan = await service.plan({"request": "Build something", "tasks": 1})
    run = await service.run({"request": "Build something", "tasks": 1})
    assert len(plan["tasks"]) == 1
    assert run["run_id"].startswith("run-")
    assert service.get_run(run["run_id"]) is not None


@pytest.mark.asyncio
async def test_github_mock_records_branch_and_pr() -> None:
    provider = MockGitHubProvider()
    config = RMAOConfig(
        mode="mock",
        llm=LLMConfig(provider="fake"),
        execution=ExecutionConfig(provider="mock"),
    )
    orchestrator = build_orchestrator(config, task_count=1)
    summary = await orchestrator.run("Build something", task_count=1)
    assert summary.merge_results
    # The independent provider contract is covered directly below.
    result = await provider.publish_task(
        "run-direct",
        PlannedTask(
            task_id="one",
            name="One",
            description="One",
            branch_slug="one",
        ),
        [],
        "main",
    )
    assert result.success
    assert result.pr_url is not None