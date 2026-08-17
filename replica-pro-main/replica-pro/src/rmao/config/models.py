"""Typed configuration models."""
from pydantic import BaseModel, Field, field_validator


class LLMConfig(BaseModel):
    provider: str = Field(default="openai")
    model: str = Field(default="gpt-4o-mini")
    timeout: int = Field(default=60, ge=1, le=600)
    max_retries: int = Field(default=3, ge=0, le=10)
    api_key: str | None = None
    base_url: str | None = None

    @field_validator("provider")
    @classmethod
    def _valid_provider(cls, v: str) -> str:
        allowed = {"openai", "deepseek", "kimi", "glm", "fake"}
        if v not in allowed:
            raise ValueError(f"provider must be one of {allowed}")
        return v


class GitHubConfig(BaseModel):
    token: str | None = None
    owner: str | None = None
    repository: str | None = None
    base_url: str = "https://api.github.com"
    base_branch: str = "main"
    repo_prefix: str = Field(default="rmao")
    private: bool = True
    create_pull_requests: bool = True
    merge_pull_requests: bool = False


class ExecutionConfig(BaseModel):
    provider: str = Field(default="mock")
    worker_count: int = Field(default=4, ge=1, le=32)
    max_file_size_bytes: int = Field(default=1024 * 1024)  # 1MB
    command_timeout: int = Field(default=300, ge=1)
    allowed_commands: list[str] = Field(default_factory=lambda: ["python", "npm", "pytest"])
    workspace_dir: str = "."
    mock_delay_ms: int = Field(default=0, ge=0, le=10_000)

    @field_validator("provider")
    @classmethod
    def _valid_provider(cls, v: str) -> str:
        allowed = {"mock", "replit", "not_configured"}
        if v not in allowed:
            raise ValueError(f"provider must be one of {allowed}")
        return v


class RMAOConfig(BaseModel):
    mode: str = Field(default="mock")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    max_concurrency: int = Field(default=4, ge=1, le=32)
    task_timeout: int = Field(default=300, ge=1)
    max_tasks: int = Field(default=4, ge=1, le=16)
    log_level: str = Field(default="INFO")
    log_redact_secrets: bool = Field(default=True)

    @field_validator("mode")
    @classmethod
    def _valid_mode(cls, v: str) -> str:
        allowed = {"mock", "real", "dry_run"}
        if v not in allowed:
            raise ValueError(f"mode must be one of {allowed}")
        return v

    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v.upper()
