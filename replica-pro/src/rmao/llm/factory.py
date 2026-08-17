"""Factory for creating LLM provider instances."""
from __future__ import annotations

from ..config.models import LLMConfig
from ..domain.errors import LLMError, ConfigError
from .base import LLMProvider
from .fake_adapter import FakeLLMAdapter
from .providers.openai_adapter import OpenAIAdapter
from .providers.deepseek_adapter import DeepSeekAdapter
from .providers.kimi_adapter import KimiAdapter
from .providers.glm_adapter import GLMAdapter


class LLMFactory:
    """Create LLM provider instances driven by configuration."""

    _REGISTRY: dict[str, type[LLMProvider]] = {
        "fake": FakeLLMAdapter,
        "openai": OpenAIAdapter,
        "deepseek": DeepSeekAdapter,
        "kimi": KimiAdapter,
        "glm": GLMAdapter,
    }

    @classmethod
    def create(cls, config: LLMConfig) -> LLMProvider:
        """Create a provider instance from config."""
        provider_cls = cls._REGISTRY.get(config.provider)
        if not provider_cls:
            raise ConfigError(
                f"Unsupported LLM provider: '{config.provider}'. "
                f"Supported: {list(cls._REGISTRY.keys())}"
            )

        if config.provider != "fake" and not config.api_key:
            raise ConfigError(
                f"LLM provider '{config.provider}' requires an API key. "
                f"Set the appropriate environment variable."
            )

        return provider_cls(
            model=config.model,
            timeout=config.timeout,
            max_retries=config.max_retries,
            api_key=config.api_key,
            base_url=config.base_url,
        )

    @classmethod
    def register(cls, name: str, provider_cls: type[LLMProvider]) -> None:
        """Register a new provider type."""
        cls._REGISTRY[name] = provider_cls
