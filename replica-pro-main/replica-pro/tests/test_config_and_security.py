from __future__ import annotations

import pytest

from rmao.config.models import GitHubConfig, LLMConfig, RMAOConfig
from rmao.config.validators import validate_config
from rmao.domain.errors import ConfigError, PlanError
from rmao.domain.types import PlannedTask, TaskPlan
from rmao.logging.redaction import REDACTED, RedactingProcessor
from rmao.planner.validator import PlanValidator


def test_real_mode_requires_github_configuration() -> None:
    config = RMAOConfig(
        mode="real",
        llm=LLMConfig(provider="fake"),
        github=GitHubConfig(),
    )
    with pytest.raises(ConfigError, match="GitHub owner"):
        validate_config(config)


def test_redaction_hides_keys_headers_and_known_secret() -> None:
    processor = RedactingProcessor({"super-secret-token"})
    result = processor(None, "info", {
        "token": "super-secret-token",
        "message": "Authorization: Bearer super-secret-token",
    })
    assert result["token"] == REDACTED
    assert REDACTED in result["message"]
    assert "super-secret-token" not in result["message"]


def test_dependency_cycle_is_rejected() -> None:
    tasks = [
        PlannedTask(
            task_id="a",
            name="A",
            description="A",
            dependencies=["b"],
            branch_slug="a",
        ),
        PlannedTask(
            task_id="b",
            name="B",
            description="B",
            dependencies=["a"],
            branch_slug="b",
        ),
    ]
    with pytest.raises(PlanError, match="cycle"):
        PlanValidator().validate(TaskPlan(tasks=tasks))