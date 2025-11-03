"""Summarization service for orchestrating commit analysis."""

from pathlib import Path

from gitlab_ticker.git.services.git_service import GitService
from gitlab_ticker.summarization.domain.value_objects import CommitSummaryInput
from gitlab_ticker.summarization.repositories.interfaces import LLMAgentRepository


class SummarizationService:
    """Service for orchestrating commit summarization."""

    def __init__(
        self,
        git_service: GitService,
        llm_agent: LLMAgentRepository,
    ) -> None:
        """
        Initialize SummarizationService.

        Args:
            git_service: Service for fetching git commit data
            llm_agent: Repository for LLM-based summarization
        """
        self._git_service = git_service
        self._llm_agent = llm_agent

    def summarize_commit(self, repo_path: Path, commit_hash: str) -> str:
        """
        Generate a markdown summary for a specific commit.

        Args:
            repo_path: Path to the git repository
            commit_hash: Hash of the commit to summarize

        Returns:
            Markdown-formatted summary of the commit

        Raises:
            RuntimeError: If commit data cannot be fetched or summarization fails
        """
        try:
            # Fetch commit data with file changes
            commit_with_files = self._git_service.list_file_changes_by_commit(
                repo_path, commit_hash
            )

            # Fetch diff content
            commit_diff = self._git_service.get_commit_diff_content(repo_path, commit_hash)

            # Create input data
            input_data = CommitSummaryInput(
                commit=commit_with_files,
                diff=commit_diff,
            )

            # Generate summary using LLM agent
            summary = self._llm_agent.summarize_commit(input_data)

            return summary
        except Exception as e:
            raise RuntimeError(
                f"Failed to summarize commit {commit_hash}: {str(e)}"
            ) from e

