"""Base LLM provider interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel


class StructuredOutput(BaseModel):
    """Result of a structured JSON generation request."""
    data: dict[str, Any]
    model: str = ""
    provider: str = ""
    usage_tokens: int | None = None


class LLMResponse(BaseModel):
    """Result of a plain text generation request."""
    text: str
    model: str = ""
    provider: str = ""
    usage_tokens: int | None = None


class LLMProvider(ABC):
    """Common interface for all LLM providers."""

    def __init__(self, model: str, timeout: int = 60, max_retries: int = 3):
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @property
    @abstractmethod
    def supports_json_mode(self) -> bool: ...

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
        system_prompt: str | None = None,
    ) -> StructuredOutput:
        """Generate structured JSON output."""
        ...

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate plain text output."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Check if the provider is configured and reachable."""
        ...
