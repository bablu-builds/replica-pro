from __future__ import annotations

import asyncio
from typing import Any

import pytest

from rmao.providers.replit import ReplitProvider, ReplitRateLimitError


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self.status = status
        self._payload = payload

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def text(self) -> str:
        import json

        return json.dumps(self._payload)


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_replit_provider_creates_and_writes_with_connect_sid_cookie() -> None:
    session = FakeSession(
        [
            FakeResponse({"data": {"createRepl": {"id": "repl-123"}}}),
            FakeResponse({"data": {"writeFile": {"success": True, "path": "main.py"}}}),
        ]
    )
    provider = ReplitProvider(
        {"ACCOUNT1_SID": "session-value"},
        session=session,
        sleep=lambda _: asyncio.sleep(0),
    )

    repl_id = await provider.create_repl("Demo", "python")
    result = await provider.write_file(repl_id, "main.py", "print('ok')")

    assert repl_id == "repl-123"
    assert result["success"] is True
    assert session.calls[0]["cookies"] == {"connect.sid": "session-value"}
    assert "session-value" not in session.calls[0]["headers"].values()


@pytest.mark.asyncio
async def test_replit_provider_rotates_after_expired_session() -> None:
    session = FakeSession(
        [
            FakeResponse({"errors": [{"message": "Session expired"}]}),
            FakeResponse({"data": {"createRepl": {"id": "repl-456"}}}),
        ]
    )
    provider = ReplitProvider(
        {"ACCOUNT1_SID": "expired", "ACCOUNT2_SID": "valid"},
        session=session,
        sleep=lambda _: asyncio.sleep(0),
    )

    assert await provider.create_repl("Demo", "python") == "repl-456"
    assert session.calls[0]["cookies"] == {"connect.sid": "expired"}
    assert session.calls[1]["cookies"] == {"connect.sid": "valid"}


@pytest.mark.asyncio
async def test_replit_provider_rejects_missing_sessions() -> None:
    provider = ReplitProvider({}, session=FakeSession([]))
    with pytest.raises(Exception, match="No Replit sessions configured"):
        await provider.create_repl("Demo", "python")