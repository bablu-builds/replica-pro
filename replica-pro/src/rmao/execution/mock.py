"""Deterministic execution provider for local development and tests."""
from __future__ import annotations

import asyncio
import hashlib

from ..domain.types import ExecutionResult, FileArtifact, PlannedTask
from ..domain.errors import ExecutionError
from .base import ExecutionProvider


class MockExecutionProvider(ExecutionProvider):
    """Generate explicit mock artifacts without running arbitrary commands."""

    def __init__(
        self,
        delay_ms: int = 0,
        fail_task_ids: set[str] | None = None,
    ) -> None:
        self.delay_ms = delay_ms
        self.fail_task_ids = fail_task_ids or set()

    @property
    def provider_name(self) -> str:
        return "mock"

    async def execute(
        self,
        task: PlannedTask,
        run_id: str,
        cancel_event: asyncio.Event | None = None,
    ) -> ExecutionResult:
        if cancel_event and cancel_event.is_set():
            return ExecutionResult(
                task_id=task.task_id,
                success=False,
                error_message="Task cancelled before mock execution",
            )
        if self.delay_ms:
            await asyncio.sleep(self.delay_ms / 1000)
        if task.task_id in self.fail_task_ids:
            raise ExecutionError(f"Mock execution failure requested for '{task.task_id}'")

        artifacts: list[FileArtifact] = []
        for path in task.expected_output_files:
            content = (
                f"# Mock artifact generated for {task.task_id}\n"
                f"# Run: {run_id}\n"
                f"# Description: {task.description}\n"
            )
            artifacts.append(
                FileArtifact(
                    path=path,
                    content=content,
                    checksum=hashlib.sha256(content.encode()).hexdigest(),
                    task_id=task.task_id,
                    verified=True,
                )
            )
        return ExecutionResult(
            task_id=task.task_id,
            success=True,
            artifacts=artifacts,
            stdout=f"Mock execution completed for {task.task_id}",
            exit_code=0,
        )