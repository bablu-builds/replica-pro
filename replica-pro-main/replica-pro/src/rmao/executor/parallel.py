"""Dependency-aware bounded parallel executor."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from ..domain.errors import AgentPoolError, ExecutionError
from ..domain.types import (
    ExecutionResult,
    PlannedTask,
    ProgressEvent,
    TaskPlan,
)
from ..execution.base import ExecutionProvider
from ..logging.redaction import get_logger
from ..pool.pool import AgentPool

logger = get_logger("rmao.executor")


@dataclass
class ExecutionReport:
    """Results and progress emitted by one plan execution."""

    results: dict[str, ExecutionResult] = field(default_factory=dict)
    events: list[ProgressEvent] = field(default_factory=list)


class ParallelExecutor:
    """Run independent tasks concurrently and honor dependencies between waves."""

    def __init__(
        self,
        provider: ExecutionProvider,
        pool: AgentPool,
        max_concurrency: int = 4,
        task_timeout: int = 300,
        on_event: Callable[[ProgressEvent], Awaitable[None] | None] | None = None,
    ) -> None:
        self.provider = provider
        self.pool = pool
        self.max_concurrency = max(1, max_concurrency)
        self.task_timeout = task_timeout
        self.on_event = on_event

    async def execute(
        self,
        plan: TaskPlan,
        run_id: str,
        cancel_event: asyncio.Event | None = None,
    ) -> ExecutionReport:
        report = ExecutionReport()
        pending = {task.task_id: task for task in plan.tasks}
        while pending:
            if cancel_event and cancel_event.is_set():
                for task in pending.values():
                    report.results[task.task_id] = self._cancelled(task)
                    await self._emit(report, run_id, "task_cancelled", task, "Cancelled")
                break

            blocked = [
                task
                for task in pending.values()
                if any(
                    dependency in report.results
                    and not report.results[dependency].success
                    for dependency in task.dependencies
                )
            ]
            for task in blocked:
                report.results[task.task_id] = ExecutionResult(
                    task_id=task.task_id,
                    success=False,
                    error_message="Blocked by a failed or cancelled dependency",
                )
                pending.pop(task.task_id)
                await self._emit(
                    report,
                    run_id,
                    "task_blocked",
                    task,
                    "Blocked by dependency failure",
                )

            if not pending:
                break

            ready = [
                task
                for task in pending.values()
                if all(dependency in report.results for dependency in task.dependencies)
            ]
            if not ready:
                raise ExecutionError("No executable tasks remain; plan dependencies are cyclic")

            wave = ready[: self.max_concurrency]
            results = await asyncio.gather(
                *(self._execute_one(task, run_id, cancel_event, report) for task in wave)
            )
            for task, result in zip(wave, results):
                report.results[task.task_id] = result
                pending.pop(task.task_id, None)
        return report

    async def close(self) -> None:
        """Close provider resources when the orchestrator lifecycle ends."""
        close = getattr(self.provider, "close", None)
        if close:
            result = close()
            if asyncio.iscoroutine(result):
                await result

    async def _execute_one(
        self,
        task: PlannedTask,
        run_id: str,
        cancel_event: asyncio.Event | None,
        report: ExecutionReport,
    ) -> ExecutionResult:
        started = time.monotonic()
        await self._emit(report, run_id, "task_queued", task, "Task queued")
        try:
            async with await self.pool.acquire(task.task_id, run_id, cancel_event):
                await self._emit(report, run_id, "task_started", task, "Task started")
                result = await asyncio.wait_for(
                    self.provider.execute(task, run_id, cancel_event),
                    timeout=self.task_timeout,
                )
                result.duration_seconds = time.monotonic() - started
                await self._emit(
                    report,
                    run_id,
                    "task_completed" if result.success else "task_failed",
                    task,
                    result.error_message or "Task finished",
                )
                return result
        except (asyncio.TimeoutError, AgentPoolError, ExecutionError) as error:
            logger.error("task_execution_failed", task_id=task.task_id, error=str(error))
            result = ExecutionResult(
                task_id=task.task_id,
                success=False,
                duration_seconds=time.monotonic() - started,
                error_message=str(error),
            )
            await self._emit(report, run_id, "task_failed", task, str(error))
            return result
        except asyncio.CancelledError:
            return self._cancelled(task, time.monotonic() - started)

    async def _emit(
        self,
        report: ExecutionReport,
        run_id: str,
        event_type: str,
        task: PlannedTask,
        message: str,
    ) -> None:
        event = ProgressEvent(
            run_id=run_id,
            event_type=event_type,
            task_id=task.task_id,
            message=message,
        )
        report.events.append(event)
        if self.on_event:
            outcome = self.on_event(event)
            if asyncio.iscoroutine(outcome):
                await outcome

    @staticmethod
    def _cancelled(task: PlannedTask, duration: float = 0.0) -> ExecutionResult:
        return ExecutionResult(
            task_id=task.task_id,
            success=False,
            duration_seconds=duration,
            error_message="Task cancelled",
        )