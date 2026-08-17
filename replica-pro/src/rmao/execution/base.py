"""Provider-neutral execution contract."""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from ..domain.types import ExecutionResult, PlannedTask


class ExecutionProvider(ABC):
    """Execute one planned task in a controlled environment."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable provider identifier for logs and summaries."""

    @abstractmethod
    async def execute(
        self,
        task: PlannedTask,
        run_id: str,
        cancel_event: asyncio.Event | None = None,
    ) -> ExecutionResult:
        """Execute a task and return a sanitized result."""