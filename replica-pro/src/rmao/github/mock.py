"""In-memory GitHub provider for tests and safe mock mode."""
from __future__ import annotations

from ..domain.types import FileArtifact, MergeResult, PlannedTask
from .base import GitHubProvider


class MockGitHubProvider(GitHubProvider):
    """Record branch/file/PR operations without network access."""

    def __init__(self, owner: str = "mock-owner", repository: str = "mock-repo") -> None:
        self.owner = owner
        self.repository = repository
        self.branches: dict[str, dict[str, str]] = {}
        self.pull_requests: list[dict[str, str]] = []

    async def publish_task(
        self,
        run_id: str,
        task: PlannedTask,
        artifacts: list[FileArtifact],
        base_branch: str,
        create_pull_request: bool = True,
        merge_pull_request: bool = False,
    ) -> MergeResult:
        branch = f"rmao/{run_id}/{task.branch_slug}"
        self.branches[branch] = {artifact.path: artifact.content for artifact in artifacts}
        pr_url = None
        if create_pull_request:
            number = len(self.pull_requests) + 1
            pr_url = f"https://github.com/{self.owner}/{self.repository}/pull/{number}"
            self.pull_requests.append(
                {
                    "number": str(number),
                    "branch": branch,
                    "base": base_branch,
                    "title": f"RMAO: {task.name}",
                }
            )
        return MergeResult(
            task_id=task.task_id,
            success=True,
            pr_url=pr_url,
            branch_name=branch,
        )