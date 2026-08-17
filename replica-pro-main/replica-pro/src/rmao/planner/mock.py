"""Deterministic planning data used only by explicit mock mode."""
from __future__ import annotations


def build_mock_plan(task_count: int) -> dict[str, object]:
    tasks = [
        {
            "task_id": f"task-{index}",
            "name": f"Implementation task {index}",
            "description": "Implement and verify the assigned scope.",
            "responsibilities": ["Implement and verify the assigned scope"],
            "dependencies": [],
            "technology_constraints": [],
            "expected_output_files": [f"generated/task-{index}.md"],
            "branch_slug": f"task-{index}",
            "acceptance_criteria": ["The assigned scope is implemented and verified"],
        }
        for index in range(1, task_count + 1)
    ]
    return {"tasks": tasks, "summary": "Deterministic mock plan generated."}