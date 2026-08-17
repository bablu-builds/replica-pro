"""Explicit placeholder for an official Replit execution integration."""
from __future__ import annotations

import asyncio

from ..domain.errors import ExecutionError
from ..domain.types import ExecutionResult, PlannedTask
from .base import ExecutionProvider


class ReplitExecutionProvider(ExecutionProvider):
    """Fail clearly until an official execution API is configured."""

    @property
    def provider_name(self) -> str:
        return "replit"

    async def execute(
        self,
        task: PlannedTask,
        run_id: str,
        cancel_event: asyncio.Event | None = None,
    ) -> ExecutionResult:
        raise ExecutionError(
            "Replit execution provider is unavailable: configure an official "
            "execution API before using real worker execution."
        )