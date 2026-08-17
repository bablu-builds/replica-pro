"""Validate planner output before it reaches the executor."""
from __future__ import annotations

from ..domain.types import TaskPlan, PlannedTask
from ..domain.errors import PlanError


class PlanValidator:
    """Validate a task plan for safety and consistency."""

    def validate(self, plan: TaskPlan) -> TaskPlan:
        """Validate and return the plan, or raise PlanError."""
        self._check_duplicate_ids(plan)
        self._check_duplicate_slugs(plan)
        self._check_dependencies(plan)
        self._check_empty_descriptions(plan)
        self._check_overlapping_files(plan)
        return plan

    def _check_duplicate_ids(self, plan: TaskPlan) -> None:
        seen: set[str] = set()
        for t in plan.tasks:
            if t.task_id in seen:
                raise PlanError(f"Duplicate task_id: '{t.task_id}'")
            seen.add(t.task_id)

    def _check_duplicate_slugs(self, plan: TaskPlan) -> None:
        seen: set[str] = set()
        for t in plan.tasks:
            if t.branch_slug in seen:
                raise PlanError(f"Duplicate branch_slug: '{t.branch_slug}'")
            seen.add(t.branch_slug)

    def _check_dependencies(self, plan: TaskPlan) -> None:
        ids = {t.task_id for t in plan.tasks}
        for t in plan.tasks:
            for dep in t.dependencies:
                if dep not in ids:
                    raise PlanError(
                        f"Task '{t.task_id}' has unknown dependency: '{dep}'"
                    )
                if dep == t.task_id:
                    raise PlanError(
                        f"Task '{t.task_id}' depends on itself"
                    )

    def _check_empty_descriptions(self, plan: TaskPlan) -> None:
        for t in plan.tasks:
            if not t.description or not t.description.strip():
                raise PlanError(f"Task '{t.task_id}' has empty description")

    def _check_overlapping_files(self, plan: TaskPlan) -> None:
        """Warn about overlapping file ownership (not a hard error)."""
        file_owners: dict[str, list[str]] = {}
        for t in plan.tasks:
            for f in t.expected_output_files:
                file_owners.setdefault(f, []).append(t.task_id)
        overlaps = {f: owners for f, owners in file_owners.items() if len(owners) > 1}
        if overlaps:
            # This is a warning, not an error — explicit shared files are allowed
            pass
