"""Validate configuration at startup with actionable errors."""
from .models import RMAOConfig
from ..domain.errors import ConfigError


def validate_config(config: RMAOConfig) -> None:
    """Validate that the configuration is usable for the selected mode."""
    errors: list[str] = []

    if config.mode == "real":
        if not config.llm.api_key and config.llm.provider != "fake":
            errors.append(
                f"LLM API key is required for real mode with provider "
                f"'{config.llm.provider}'. Set the appropriate API key "
                "environment variable (e.g., OPENAI_API_KEY)."
            )

        if config.execution.provider == "replit":
            errors.append(
                "Replit execution provider is not yet fully configured. "
                "Use 'mock' execution provider or wait for official Replit API support."
            )

        if not config.github.token:
            errors.append("GitHub token is required for real mode. Set GITHUB_TOKEN.")

        if not config.github.owner:
            errors.append("GitHub owner is required for real mode. Set GITHUB_OWNER.")

    if config.mode == "dry_run":
        if config.llm.provider != "fake" and not config.llm.api_key:
            errors.append(
                "Dry-run mode still requires an LLM for planning. "
                "Use fake LLM provider or provide an API key."
            )

    if errors:
        details = "\n".join(f"  - {error}" for error in errors)
        raise ConfigError(
            f"Configuration validation failed ({len(errors)} error(s)):\n{details}"
        )
