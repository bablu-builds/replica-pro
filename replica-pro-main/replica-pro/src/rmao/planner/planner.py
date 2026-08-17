"""Task planner that turns a user request into validated parallel tasks."""
from typing import Any

from ..llm.base import LLMProvider
from ..domain.types import TaskPlan, PlannedTask
from ..domain.errors import PlanError, LLMError
from ..logging.redaction import get_logger
from .prompts import PLANNER_SYSTEM_PROMPT, build_planner_prompt
from .validator import PlanValidator

logger = get_logger("rmao.planner")


class TaskPlanner:
    """Plan tasks from a user project request."""

    MIN_TASKS = 1
    MAX_TASKS = 16
    DEFAULT_TASKS = 4

    def __init__(self, llm: LLMProvider, validator: PlanValidator | None = None):
        self.llm = llm
        self.validator = validator or PlanValidator()

    async def plan(self, user_request: str, num_tasks: int | None = None) -> TaskPlan:
        """Generate a validated task plan."""
        num = self._clamp_num_tasks(num_tasks or self.DEFAULT_TASKS)
        prompt = build_planner_prompt(user_request, num)
        logger.info("planning_started", request_chars=len(user_request), num_tasks=num)

        try:
            response = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt=PLANNER_SYSTEM_PROMPT,
            )
        except LLMError as error:
            logger.error("llm_planning_failed", error=str(error))
            raise PlanError(f"LLM planning failed: {error}") from error

        plan = self._parse_response(response.data)
        plan = self.validator.validate(plan)
        logger.info("planning_completed", task_count=len(plan.tasks))
        return plan

    def _parse_response(self, data: dict[str, Any]) -> TaskPlan:
        if not isinstance(data, dict):
            raise PlanError("Planner response is not a JSON object")

        raw_tasks = data.get("tasks")
        if not isinstance(raw_tasks, list):
            raise PlanError("Planner response missing 'tasks' array")

        tasks: list[PlannedTask] = []
        for index, raw_task in enumerate(raw_tasks):
            if not isinstance(raw_task, dict):
                raise PlanError(f"Task {index} is not an object")
            try:
                tasks.append(PlannedTask(**raw_task))
            except Exception as error:
                raise PlanError(f"Task {index} validation failed: {error}") from error

        return TaskPlan(tasks=tasks, summary=data.get("summary", ""))

    def _clamp_num_tasks(self, number: int) -> int:
        return max(self.MIN_TASKS, min(number, self.MAX_TASKS))

    def summarize(self, plan: TaskPlan) -> str:
        """Return a read-only summary for CLI/API display."""
        lines = [f"Plan: {plan.summary}", f"Tasks ({len(plan.tasks)}):"]
        for task in plan.tasks:
            dependencies = (
                f" (depends: {', '.join(task.dependencies)})"
                if task.dependencies
                else ""
            )
            lines.append(f"  - {task.task_id}: {task.name}{dependencies}")
        return "\n".join(lines)
