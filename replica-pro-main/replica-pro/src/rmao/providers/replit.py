"""Async provider for the Replit GraphQL endpoint.

Replit does not currently publish a supported Python automation SDK for the
operations used here.  This provider keeps the small HTTP boundary isolated so
the rest of RMAO can remain provider-neutral.  The endpoint and operation
shapes are configurable in one place because internal APIs can change.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

import aiohttp
from dotenv import load_dotenv


DEFAULT_ENDPOINT = "https://replit.com/graphql"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 3
MAX_FILE_SIZE_BYTES = 1024 * 1024


class ReplitProviderError(RuntimeError):
    """The Replit API rejected or could not complete a request."""


class ReplitAuthenticationError(ReplitProviderError):
    """The configured connect.sid cookie is missing or expired."""


class ReplitRateLimitError(ReplitProviderError):
    """The Replit API continued rate limiting after retries."""


@dataclass(frozen=True)
class _Account:
    """A named Replit account session."""

    name: str
    sid: str


_QUERIES: dict[str, str] = {
    "CreateRepl": """
        mutation CreateRepl($title: String!, $language: String!) {
          createRepl(title: $title, language: $language) {
            id
            title
            language
            url
          }
        }
    """,
    "WriteFile": """
        mutation WriteFile($replId: ID!, $path: String!, $content: String!) {
          writeFile(replId: $replId, path: $path, content: $content) {
            success
            path
          }
        }
    """,
    "RunCommand": """
        mutation RunCommand($replId: ID!, $command: String!) {
          runCommand(replId: $replId, command: $command) {
            success
            exitCode
            stdout
            stderr
          }
        }
    """,
}


class ReplitProvider:
    """Call Replit's GraphQL operations with rotating connect.sid sessions.

    The provider is intentionally lazy: constructing it without environment
    variables is safe, while the first API call fails with a clear
    configuration error.  This keeps mock mode and local tests credential-free.
    """

    def __init__(
        self,
        account_sids: Mapping[str, str] | None = None,
        *,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        session: Any | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        load_dotenv()
        raw_sids = account_sids if account_sids is not None else self._read_env_sids()
        self._accounts = [
            _Account(name=name, sid=sid.strip())
            for name, sid in raw_sids.items()
            if isinstance(sid, str) and sid.strip()
        ]
        self.endpoint = endpoint.rstrip("/")
        self.timeout = max(1, timeout)
        self.max_retries = max(0, max_retries)
        self._session = session
        self._owns_session = session is None
        self._sleep = sleep
        self._account_cursor = 0

    @staticmethod
    def _read_env_sids() -> dict[str, str]:
        """Read all supported account sessions without exposing their values."""
        return {
            f"ACCOUNT{index}_SID": os.getenv(f"ACCOUNT{index}_SID", "")
            for index in range(1, 5)
        }

    async def __aenter__(self) -> "ReplitProvider":
        await self._get_session()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close a session created by this provider."""
        if self._owns_session and self._session is not None:
            close = getattr(self._session, "close", None)
            if close:
                result = close()
                if hasattr(result, "__await__"):
                    await result
            self._session = None

    async def create_repl(self, title: str, language: str) -> str:
        """Create a Repl and return its stable identifier."""
        title = title.strip()
        language = language.strip().lower()
        if not title:
            raise ValueError("Repl title must not be empty")
        if not language or len(language) > 32:
            raise ValueError("Repl language must be a non-empty short name")

        data = await self._graphql(
            "CreateRepl",
            {"title": title[:128], "language": language},
        )
        repl = self._payload(data, "createRepl", "repl", "create_repl")
        repl_id = repl.get("id") or repl.get("replId")
        if not isinstance(repl_id, str) or not repl_id:
            raise ReplitProviderError("Replit createRepl response did not contain an id")
        return repl_id

    async def write_file(self, repl_id: str, path: str, content: str) -> dict[str, Any]:
        """Write a UTF-8 file into an existing Repl."""
        self._validate_repl_id(repl_id)
        self._validate_path(path)
        if not isinstance(content, str):
            raise TypeError("File content must be a string")
        if len(content.encode("utf-8")) > MAX_FILE_SIZE_BYTES:
            raise ValueError("File content exceeds the 1 MiB provider limit")

        data = await self._graphql(
            "WriteFile",
            {"replId": repl_id, "path": path, "content": content},
        )
        return self._payload(data, "writeFile", "file", "write_file")

    async def run_command(self, repl_id: str, command: str) -> dict[str, Any]:
        """Run a command in an existing Repl and return its result payload."""
        self._validate_repl_id(repl_id)
        command = command.strip()
        if not command:
            raise ValueError("Command must not be empty")
        if len(command) > 4096:
            raise ValueError("Command is too long")

        data = await self._graphql(
            "RunCommand",
            {"replId": repl_id, "command": command},
        )
        return self._payload(data, "runCommand", "command", "run_command")

    async def _get_session(self) -> Any:
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _graphql(
        self,
        operation_name: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        if operation_name not in _QUERIES:
            raise ReplitProviderError(f"Unsupported GraphQL operation: {operation_name}")
        if not self._accounts:
            raise ReplitAuthenticationError(
                "No Replit sessions configured; set ACCOUNT1_SID through ACCOUNT4_SID"
            )

        payload = {
            "operationName": operation_name,
            "query": _QUERIES[operation_name],
            "variables": variables,
        }
        last_error: Exception | None = None
        start = self._account_cursor % len(self._accounts)

        for account_offset in range(len(self._accounts)):
            account = self._accounts[(start + account_offset) % len(self._accounts)]
            for attempt in range(self.max_retries + 1):
                try:
                    response = await self._post(account, payload)
                    self._account_cursor = (
                        start + account_offset + 1
                    ) % len(self._accounts)
                    return response
                except ReplitAuthenticationError as error:
                    last_error = error
                    break
                except ReplitRateLimitError as error:
                    last_error = error
                    if attempt >= self.max_retries:
                        break
                    await self._sleep(self._backoff(attempt))
                except ReplitProviderError as error:
                    last_error = error
                    if attempt >= self.max_retries or not self._retryable(error):
                        break
                    await self._sleep(self._backoff(attempt))

        if last_error:
            raise last_error
        raise ReplitProviderError("Replit request failed without a response")

    async def _post(
        self,
        account: _Account,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        session = await self._get_session()
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://replit.com",
            "Referer": "https://replit.com/",
            "User-Agent": "rmao-replit-provider/1.0",
        }
        try:
            async with session.post(
                self.endpoint,
                json=payload,
                headers=headers,
                cookies={"connect.sid": account.sid},
            ) as response:
                body = await response.text()
                if response.status in {401, 403}:
                    raise ReplitAuthenticationError(
                        f"Replit session {account.name} is expired or unauthorized"
                    )
                if response.status == 429:
                    raise ReplitRateLimitError("Replit API rate limit exceeded")
                if response.status >= 500:
                    raise ReplitProviderError(
                        f"Replit API server error ({response.status})"
                    )
                if response.status >= 400:
                    raise ReplitProviderError(
                        f"Replit API request failed ({response.status})"
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            raise ReplitProviderError(f"Replit network request failed: {error}") from error

        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as error:
            raise ReplitProviderError("Replit returned a non-JSON response") from error

        if not isinstance(decoded, dict):
            raise ReplitProviderError("Replit returned an invalid GraphQL response")
        errors = decoded.get("errors")
        if errors:
            message = self._graphql_error_message(errors)
            normalized = message.lower()
            if any(term in normalized for term in ("unauthorized", "forbidden", "session", "login")):
                raise ReplitAuthenticationError(message)
            if "rate" in normalized or "limit" in normalized:
                raise ReplitRateLimitError(message)
            raise ReplitProviderError(message)
        data = decoded.get("data")
        if not isinstance(data, dict):
            raise ReplitProviderError("Replit GraphQL response did not contain data")
        return data

    @staticmethod
    def _graphql_error_message(errors: Any) -> str:
        if isinstance(errors, list):
            messages = [
                item.get("message")
                for item in errors
                if isinstance(item, dict) and isinstance(item.get("message"), str)
            ]
            if messages:
                return "; ".join(messages)
        return "Replit GraphQL request failed"

    @staticmethod
    def _payload(data: dict[str, Any], *keys: str) -> dict[str, Any]:
        for key in keys:
            value = data.get(key)
            if isinstance(value, dict):
                return value
        raise ReplitProviderError("Replit GraphQL response had an unexpected shape")

    @staticmethod
    def _validate_repl_id(repl_id: str) -> None:
        if not isinstance(repl_id, str) or not repl_id.strip():
            raise ValueError("Repl id must not be empty")

    @staticmethod
    def _validate_path(path: str) -> None:
        if (
            not isinstance(path, str)
            or not path.strip()
            or path.startswith("/")
            or "\\" in path
            or any(part in {"", ".", ".."} for part in path.split("/"))
        ):
            raise ValueError("File path must be a safe relative path")

    @staticmethod
    def _backoff(attempt: int) -> float:
        # Small jitter prevents four configured accounts retrying in lockstep.
        return min(30.0, (2**attempt) + random.uniform(0, 0.25))

    @staticmethod
    def _retryable(error: ReplitProviderError) -> bool:
        return "server error" in str(error).lower() or "network" in str(error).lower()