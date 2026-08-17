
"""Shared domain types for the orchestrator."""
from __future__ import annotations

from enum import Enum
from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class TaskStatus(str, Enum):
    pending = "pending"
    queued = "queued"
    running = "running"
    file_generation = "file_generation"
    verifying = "verifying"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class WorkerStatus(str, Enum):
    idle = "idle"
    busy = "busy"
    failed = "failed"
    offline = "offline"


class RunState(str, Enum):
    created = "created"
    planning = "planning"
    planned = "planned"
    executing = "executing"
    partially_failed = "partially_failed"
    execution_failed = "execution_failed"
    ready_for_merge = "ready_for_merge"
    merged = "merged"
    cancelled = "cancelled"
    completed_with_warnings = "completed_with_warnings"


class PlannedTask(BaseModel):
    """A single planned task ready for execution."""
    task_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(..., min_length=1)
    responsibilities: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    technology_constraints: list[str] = Field(default_factory=list)
    expected_output_files: list[str] = Field(default_factory=list)
    port: int | None = Field(default=None, ge=1, le=65535)
    branch_slug: str = Field(..., min_length=1, max_length=64)
    acceptance_criteria: list[str] = Field(default_factory=list)

    @field_validator("task_id", "branch_slug")
    @classmethod
    def _safe_slug(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
            raise ValueError("must be alphanumeric with hyphens/underscores only")
        return v

    @field_validator("expected_output_files")
    @classmethod
    def _safe_paths(cls, files: list[str]) -> list[str]:
        for f in files:
            if f.startswith("/") or ".." in f:
                raise ValueError(f"unsafe path: {f}")
        return files


class TaskPlan(BaseModel):
    """Validated plan produced by the task planner."""
    tasks: list[PlannedTask] = Field(..., min_length=1, max_length=16)
    summary: str = ""

    def get_task(self, task_id: str) -> PlannedTask | None:
        for t in self.tasks:
            if t.task_id == task_id:
                return t
        return None

    def dependency_order(self) -> list[PlannedTask]:
        """Return tasks in dependency-respecting order."""
        visited: set[str] = set()
        ordered: list[PlannedTask] = []

        def visit(t: PlannedTask):
            if t.task_id in visited:
                return
            for dep in t.dependencies:
                dep_task = self.get_task(dep)
                if dep_task:
                    visit(dep_task)
            visited.add(t.task_id)
            ordered.append(t)

        for task in self.tasks:
            visit(task)
        return ordered


class FileArtifact(BaseModel):
    """A generated file with metadata."""
    path: str
    content: str
    checksum: str = ""
    task_id: str = ""
    verified: bool = False

    @field_validator("path")
    @classmethod
    def _safe_path(cls, v: str) -> str:
        if v.startswith("/") or ".." in v:
            raise ValueError("unsafe file path")
        return v


class ExecutionResult(BaseModel):
    """Result of executing a single task."""
    task_id: str
    success: bool
    artifacts: list[FileArtifact] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    duration_seconds: float = 0.0
    error_message: str | None = None


class MergeResult(BaseModel):
    """Result of a Git merge operation."""
    task_id: str
    success: bool
    pr_url: str | None = None
    branch_name: str | None = None
    conflict_detected: bool = False
    error_message: str | None = None


class WorkerRecord(BaseModel):
    """A worker/agent in the pool."""
    worker_id: str
    capabilities: list[str] = Field(default_factory=list)
    provider_ref: str = "mock"
    status: WorkerStatus = WorkerStatus.idle
    current_task_id: str | None = None
    current_run_id: str | None = None
    last_heartbeat: datetime | None = None
    last_error: str | None = None


class OrchestratorRunSummary(BaseModel):
    """Final summary of an orchestrator run."""
    run_id: str
    state: RunState
    plan: TaskPlan | None = None
    task_results: dict[str, ExecutionResult] = Field(default_factory=dict)
    merge_results: dict[str, MergeResult] = Field(default_factory=dict)
    pr_links: list[str] = Field(default_factory=list)
    repo_url: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    cancelled: bool = False


class ProgressEvent(BaseModel):
    """A progress event emitted during a run."""
    run_id: str
    event_type: str
    task_id: str | None = None
    message: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
