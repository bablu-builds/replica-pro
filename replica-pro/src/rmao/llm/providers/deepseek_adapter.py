"""DeepSeek LLM adapter (OpenAI-compatible)."""
from .openai_adapter import OpenAIAdapter


class DeepSeekAdapter(OpenAIAdapter):
    """DeepSeek uses OpenAI-compatible API."""

    def __init__(
        self,
        model: str = "deepseek-chat",
        timeout: int = 60,
        max_retries: int = 3,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        super().__init__(
            model=model,
            timeout=timeout,
            max_retries=max_retries,
            api_key=api_key,
            base_url=base_url or "https://api.deepseek.com/v1",
        )

    @property
    def provider_name(self) -> str:
        return "deepseek"
