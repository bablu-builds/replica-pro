"""Execution adapter backed by the custom Replit provider."""
from __future__ import annotations

import asyncio
import json
import os
import time

from ..domain.errors import ExecutionError
from ..domain.types import ExecutionResult, PlannedTask
from ..providers.replit import ReplitProvider, ReplitProviderError
from .base import ExecutionProvider


class ReplitExecutionProvider(ExecutionProvider):
    """Create a Repl, upload a task manifest, and optionally run a command.

    Planning currently produces file names rather than file contents.  The
    manifest makes that limitation explicit instead of pretending generated
    source exists.  Set RMAO_REPLIT_COMMAND when a downstream agent should run
    a command after the manifest is uploaded.
    """

    def __init__(
        self,
        provider: ReplitProvider | None = None,
        *,
        language: str | None = None,
        command: str | None = None,
    ) -> None:
        self.provider = provider or ReplitProvider()
        self.language = language or os.getenv("RMAO_REPLIT_LANGUAGE", "python")
        self.command = command if command is not None else os.getenv("RMAO_REPLIT_COMMAND")

    @property
    def provider_name(self) -> str:
        return "replit"

    async def execute(
        self,
        task: PlannedTask,
        run_id: str,
        cancel_event: asyncio.Event | None = None,
    ) -> ExecutionResult:
        started = time.monotonic()
        if cancel_event and cancel_event.is_set():
            return ExecutionResult(
                task_id=task.task_id,
                success=False,
                error_message="Task cancelled before Replit execution",
            )

        try:
            repl_id = await self.provider.create_repl(task.name, self.language)
            manifest = json.dumps(
                {
                    "run_id": run_id,
                    "task_id": task.task_id,
                    "name": task.name,
                    "description": task.description,
                    "responsibilities": task.responsibilities,
                    "expected_output_files": task.expected_output_files,
                    "acceptance_criteria": task.acceptance_criteria,
                },
                indent=2,
            )
            await self.provider.write_file(repl_id, ".rmao/task.json", manifest)

            if self.command:
                command_result = await self.provider.run_command(repl_id, self.command)
                exit_code = command_result.get("exitCode")
                success = bool(command_result.get("success", exit_code in (None, 0)))
                return ExecutionResult(
                    task_id=task.task_id,
                    success=success,
                    stdout=str(command_result.get("stdout", "")),
                    stderr=str(command_result.get("stderr", "")),
                    exit_code=exit_code if isinstance(exit_code, int) else None,
                    duration_seconds=time.monotonic() - started,
                    error_message=None if success else "Replit command failed",
                )

            return ExecutionResult(
                task_id=task.task_id,
                success=True,
                stdout=f"Created Repl {repl_id} and uploaded .rmao/task.json",
                exit_code=0,
                duration_seconds=time.monotonic() - started,
            )
        except (ReplitProviderError, ValueError) as error:
            raise ExecutionError(str(error)) from error

    async def close(self) -> None:
        """Release the provider's aiohttp session when the run is complete."""
        await self.provider.close()