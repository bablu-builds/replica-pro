"""Domain error types for the orchestrator."""


class RMAOError(Exception):
    """Base error for all RMAO exceptions."""
    pass


class ConfigError(RMAOError):
    """Configuration is missing or invalid."""
    pass


class ValidationError(RMAOError):
    """Input or plan validation failed."""
    pass


class ProviderError(RMAOError):
    """A provider (LLM, execution, GitHub) is unavailable or misconfigured."""
    pass


class LLMError(ProviderError):
    """LLM request failed or returned malformed output."""
    pass


class ExecutionError(ProviderError):
    """Execution environment failed."""
    pass


class AgentPoolError(RMAOError):
    """Worker allocation or lifecycle error."""
    pass


class GitHubError(ProviderError):
    """GitHub operation failed."""
    pass


class PlanError(ValidationError):
    """Planner output was invalid."""
    pass


class SecretRedactionError(RMAOError):
    """Secret could not be safely redacted."""
    pass
