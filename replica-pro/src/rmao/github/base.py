"""Provider-neutral GitHub workflow contract."""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain.types import FileArtifact, MergeResult, PlannedTask


class GitHubProvider(ABC):
    """Repository operations required by the orchestrator."""

    @abstractmethod
    async def publish_task(
        self,
        run_id: str,
        task: PlannedTask,
        artifacts: list[FileArtifact],
        base_branch: str,
        create_pull_request: bool = True,
        merge_pull_request: bool = False,
    ) -> MergeResult:
        """Publish task artifacts and optionally create/merge a pull request."""