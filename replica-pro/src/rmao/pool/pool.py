"""Bounded worker leasing with cancellation-aware waiting."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from ..domain.errors import AgentPoolError
from ..domain.types import WorkerRecord, WorkerStatus


class WorkerLease:
    """Async context manager that returns a worker to its pool."""

    def __init__(self, pool: "AgentPool", worker: WorkerRecord) -> None:
        self._pool = pool
        self.worker = worker

    async def __aenter__(self) -> WorkerRecord:
        return self.worker

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self._pool.release(self.worker.worker_id, failed=exc is not None)


class AgentPool:
    """A fixed-size pool of logical workers."""

    def __init__(self, size: int, provider_ref: str = "mock") -> None:
        if size < 1:
            raise AgentPoolError("Worker pool size must be at least 1")
        self._condition = asyncio.Condition()
        self._workers = {
            f"worker-{index}": WorkerRecord(
                worker_id=f"worker-{index}",
                provider_ref=provider_ref,
                last_heartbeat=datetime.now(timezone.utc),
            )
            for index in range(1, size + 1)
        }

    @property
    def workers(self) -> list[WorkerRecord]:
        return list(self._workers.values())

    async def acquire(
        self,
        task_id: str,
        run_id: str,
        cancel_event: asyncio.Event | None = None,
    ) -> WorkerLease:
        async with self._condition:
            while True:
                if cancel_event and cancel_event.is_set():
                    raise AgentPoolError("Worker acquisition cancelled")
                worker = next(
                    (
                        candidate
                        for candidate in self._workers.values()
                        if candidate.status == WorkerStatus.idle
                    ),
                    None,
                )
                if worker:
                    worker.status = WorkerStatus.busy
                    worker.current_task_id = task_id
                    worker.current_run_id = run_id
                    worker.last_heartbeat = datetime.now(timezone.utc)
                    return WorkerLease(self, worker)
                try:
                    await asyncio.wait_for(self._condition.wait(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue

    async def release(self, worker_id: str, failed: bool = False) -> None:
        async with self._condition:
            worker = self._workers.get(worker_id)
            if not worker:
                raise AgentPoolError(f"Unknown worker '{worker_id}'")
            worker.status = WorkerStatus.failed if failed else WorkerStatus.idle
            worker.current_task_id = None
            worker.current_run_id = None
            worker.last_heartbeat = datetime.now(timezone.utc)
            self._condition.notify_all()

    async def mark_offline(self, worker_id: str, reason: str = "") -> None:
        async with self._condition:
            worker = self._workers.get(worker_id)
            if not worker:
                raise AgentPoolError(f"Unknown worker '{worker_id}'")
            worker.status = WorkerStatus.offline
            worker.last_error = reason or None
            self._condition.notify_all()