"""OpenAI LLM adapter."""
import json
from typing import Any

from ..base import LLMProvider, LLMResponse, StructuredOutput
from ...domain.errors import LLMError


class OpenAIAdapter(LLMProvider):
    """OpenAI-compatible adapter (works with OpenAI and any OpenAI-compatible endpoint)."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        timeout: int = 60,
        max_retries: int = 3,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        super().__init__(model, timeout, max_retries)
        self._api_key = api_key
        self._base_url = base_url or "https://api.openai.com/v1"
        self._client: Any | None = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def supports_json_mode(self) -> bool:
        return True

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import openai
            except ImportError:
                raise LLMError("openai package is not installed. Install with: pip install openai")
            self._client = openai.AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self.timeout,
                max_retries=self.max_retries,
            )
        return self._client

    async def generate_structured(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
        system_prompt: str | None = None,
    ) -> StructuredOutput:
        client = self._get_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                timeout=self.timeout,
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return StructuredOutput(
                data=data,
                model=self.model,
                provider=self.provider_name,
                usage_tokens=response.usage.total_tokens if response.usage else None,
            )
        except json.JSONDecodeError as e:
            raise LLMError(f"OpenAI returned invalid JSON: {e}")
        except Exception as e:
            raise LLMError(f"OpenAI request failed: {e}")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        client = self._get_client()
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                timeout=self.timeout,
            )
            text = response.choices[0].message.content or ""
            return LLMResponse(
                text=text,
                model=self.model,
                provider=self.provider_name,
                usage_tokens=response.usage.total_tokens if response.usage else None,
            )
        except Exception as e:
            raise LLMError(f"OpenAI request failed: {e}")

    def health_check(self) -> bool:
        return self._api_key is not None and len(self._api_key) > 0
