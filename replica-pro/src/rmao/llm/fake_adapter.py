"""Deterministic fake LLM adapter for tests and mock mode."""
import json
from typing import Any

from .base import LLMProvider, LLMResponse, StructuredOutput
from ..domain.errors import LLMError


class FakeLLMAdapter(LLMProvider):
    """Fake LLM that returns deterministic, configurable responses."""

    def __init__(
        self,
        model: str = "fake-model",
        timeout: int = 60,
        max_retries: int = 3,
        api_key: str | None = None,
        base_url: str | None = None,
        structured_response: dict[str, Any] | None = None,
        text_response: str = "fake response",
    ):
        super().__init__(model, timeout, max_retries)
        self._structured = structured_response or {}
        self._text = text_response
        self._api_key = api_key
        self._base_url = base_url

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def supports_json_mode(self) -> bool:
        return True

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
        system_prompt: str | None = None,
    ) -> StructuredOutput:
        if "malformed" in prompt.lower():
            raise LLMError("Fake adapter: malformed output requested")
        if "timeout" in prompt.lower():
            raise LLMError("Fake adapter: timeout requested")
        return StructuredOutput(
            data=self._structured.copy(),
            model=self.model,
            provider=self.provider_name,
            usage_tokens=0,
        )

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        return LLMResponse(
            text=self._text,
            model=self.model,
            provider=self.provider_name,
            usage_tokens=0,
        )

    def health_check(self) -> bool:
        return True

    def set_structured_response(self, data: dict[str, Any]) -> None:
        self._structured = data

    def set_text_response(self, text: str) -> None:
        self._text = text
