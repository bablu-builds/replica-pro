"""Load configuration from environment variables."""
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

from .models import RMAOConfig, LLMConfig, GitHubConfig, ExecutionConfig
from ..domain.errors import ConfigError


def load_config(env_path: str | None = None) -> RMAOConfig:
    """Load configuration from environment variables and optional .env file."""
    if env_path and os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()

    try:
        provider = os.getenv("RMAO_LLM_PROVIDER", "fake")
        api_key_name = {
            "openai": "OPENAI_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "kimi": "KIMI_API_KEY",
            "glm": "GLM_API_KEY",
        }.get(provider)
        llm = LLMConfig(
            provider=provider,
            model=os.getenv("RMAO_LLM_MODEL", "fake-model"),
            timeout=int(os.getenv("RMAO_LLM_TIMEOUT", "60")),
            max_retries=int(os.getenv("RMAO_LLM_MAX_RETRIES", "3")),
            api_key=_read_secret(api_key_name) if api_key_name else None,
            base_url=os.getenv("RMAO_LLM_BASE_URL") or None,
        )

        github = GitHubConfig(
            token=_read_secret("GITHUB_TOKEN"),
            owner=_normalize_owner(os.getenv("GITHUB_OWNER")),
            repository=_normalize_repository(os.getenv("GITHUB_REPOSITORY")),
            base_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
            base_branch=os.getenv("GITHUB_BASE_BRANCH", "main"),
            repo_prefix=os.getenv("GITHUB_REPO_PREFIX", "rmao"),
            create_pull_requests=_read_bool("GITHUB_CREATE_PULL_REQUESTS", True),
            merge_pull_requests=_read_bool("GITHUB_MERGE_PULL_REQUESTS", False),
        )

        execution = ExecutionConfig(
            provider=os.getenv("RMAO_EXECUTION_PROVIDER", "mock"),
            worker_count=int(os.getenv("RMAO_WORKER_COUNT", "4")),
            workspace_dir=os.getenv("RMAO_WORKSPACE_DIR", "."),
            mock_delay_ms=int(os.getenv("RMAO_MOCK_DELAY_MS", "0")),
        )

        return RMAOConfig(
            mode=os.getenv("RMAO_MODE", "mock"),
            llm=llm,
            github=github,
            execution=execution,
            max_concurrency=int(os.getenv("RMAO_MAX_CONCURRENCY", "4")),
            task_timeout=int(os.getenv("RMAO_TASK_TIMEOUT", "300")),
            max_tasks=int(os.getenv("RMAO_MAX_TASKS", "4")),
            log_level=os.getenv("RMAO_LOG_LEVEL", "INFO"),
            log_redact_secrets=_read_bool("RMAO_LOG_REDACT_SECRETS", True),
        )
    except (TypeError, ValueError) as error:
        raise ConfigError(f"Invalid environment configuration: {error}") from error


def _read_secret(name: str) -> str | None:
    """Read a secret from environment. Returns None if empty."""
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()
    return None


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{name} must be true or false")
    return normalized in {"true", "1", "yes"}


def _normalize_owner(value: str | None) -> str | None:
    """Accept either a plain owner or a GitHub URL."""
    if not value:
        return None
    cleaned = value.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.netloc.lower() in {"github.com", "www.github.com"}:
        parts = [part for part in parsed.path.split("/") if part]
        return parts[0] if parts else None
    return cleaned.removeprefix("github.com/").strip("/") or None


def _normalize_repository(value: str | None) -> str | None:
    """Accept repo name, owner/repo, HTTPS URL, or SSH clone URL."""
    if not value:
        return None
    cleaned = value.strip().rstrip("/")
    if cleaned.startswith("git@github.com:"):
        cleaned = cleaned.removeprefix("git@github.com:")
    parsed = urlparse(cleaned)
    if parsed.netloc.lower() in {"github.com", "www.github.com"}:
        cleaned = parsed.path.strip("/")
    cleaned = cleaned.removesuffix(".git").strip("/")
    if "/" in cleaned:
        cleaned = cleaned.split("/")[-1]
    return cleaned or None
