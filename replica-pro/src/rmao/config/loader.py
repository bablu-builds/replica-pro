"""Load configuration from environment variables."""
import os
from dotenv import load_dotenv

from .models import RMAOConfig, LLMConfig, GitHubConfig, ExecutionConfig
from ..domain.errors import ConfigError


def load_config(env_path: str | None = None) -> RMAOConfig:
    """Load configuration from environment variables and optional .env file."""
    if env_path and os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        load_dotenv()

    llm = LLMConfig(
        provider=os.getenv("RMAO_LLM_PROVIDER", "openai"),
        model=os.getenv("RMAO_LLM_MODEL", "gpt-4o-mini"),
        timeout=int(os.getenv("RMAO_LLM_TIMEOUT", "60")),
        max_retries=int(os.getenv("RMAO_LLM_MAX_RETRIES", "3")),
        api_key=_read_secret("OPENAI_API_KEY")
                  or _read_secret("DEEPSEEK_API_KEY")
                  or _read_secret("KIMI_API_KEY")
                  or _read_secret("GLM_API_KEY"),
    )

    github = GitHubConfig(
        token=_read_secret("GITHUB_TOKEN"),
        owner=os.getenv("GITHUB_OWNER"),
        repo_prefix=os.getenv("GITHUB_REPO_PREFIX", "rmao"),
    )

    execution = ExecutionConfig(
        provider=os.getenv("RMAO_EXECUTION_PROVIDER", "mock"),
        worker_count=int(os.getenv("RMAO_WORKER_COUNT", "4")),
    )

    config = RMAOConfig(
        mode=os.getenv("RMAO_MODE", "mock"),
        llm=llm,
        github=github,
        execution=execution,
        max_concurrency=int(os.getenv("RMAO_MAX_CONCURRENCY", "4")),
        task_timeout=int(os.getenv("RMAO_TASK_TIMEOUT", "300")),
        max_tasks=int(os.getenv("RMAO_MAX_TASKS", "4")),
        log_level=os.getenv("RMAO_LOG_LEVEL", "INFO"),
        log_redact_secrets=os.getenv("RMAO_LOG_REDACT_SECRETS", "true").lower() == "true",
    )

    return config


def _read_secret(name: str) -> str | None:
    """Read a secret from environment. Returns None if empty."""
    value = os.getenv(name)
    if value and value.strip():
        return value.strip()
    return None
