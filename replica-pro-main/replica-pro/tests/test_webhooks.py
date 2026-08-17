from __future__ import annotations

from fastapi.testclient import TestClient

from rmao.api.server import create_app
from rmao.api.webhooks import extract_project_request
from rmao.config.models import ExecutionConfig, LLMConfig, RMAOConfig
from rmao.orchestration.orchestrator import build_orchestrator


def test_webhook_extracts_query_from_commit_and_config() -> None:
    query, tasks = extract_project_request(
        {
            "head_commit": {"message": "[rmao] Build a release dashboard"},
            "config": {"tasks": 3},
        }
    )
    assert query == "Build a release dashboard"
    assert tasks == 3


def test_github_webhook_requires_token(monkeypatch) -> None:
    monkeypatch.setenv("RMAO_WEBHOOK_TOKEN", "test-token")
    config = RMAOConfig(
        mode="mock",
        llm=LLMConfig(provider="fake"),
        execution=ExecutionConfig(provider="mock"),
    )
    app = create_app(config, build_orchestrator(config, task_count=1))
    client = TestClient(app)

    response = client.post(
        "/v1/webhooks/github",
        json={"project_query": "Build a webhook project"},
        headers={"X-Orchestrator-Token": "wrong-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "http_401"
    assert response.json()["error"]["message"] == "Invalid orchestrator token"