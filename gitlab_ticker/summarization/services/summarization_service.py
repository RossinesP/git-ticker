"""Summarization service for orchestrating commit analysis."""

from pathlib import Path

from gitlab_ticker.git.domain.entities import CommitWithFiles
from gitlab_ticker.git.domain.value_objects import CommitDiff, DiffSizeConfig
from gitlab_ticker.git.services.file_filter_service import FileFilterService
from gitlab_ticker.git.services.git_service import GitService
from gitlab_ticker.summarization.domain.value_objects import (
    CommitSummaryInput,
    DiffSummaryInput,
)
from gitlab_ticker.summarization.repositories.interfaces import LLMAgentRepository


class SummarizationService:
    """Service for orchestrating commit summarization."""

    def __init__(
        self,
        git_service: GitService,
        llm_agent: LLMAgentRepository,
        diff_size_config: DiffSizeConfig | None = None,
    ) -> None:
        """
        Initialize SummarizationService.

        Args:
            git_service: Service for fetching git commit data
            llm_agent: Repository for LLM-based summarization
            diff_size_config: Configuration for diff size limits. Defaults to DiffSizeConfig()
        """
        self._git_service = git_service
        self._llm_agent = llm_agent
        self._diff_size_config = diff_size_config or DiffSizeConfig()
        self._file_filter_service = FileFilterService()

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

            # Filter out generated files
            filtered_file_changes = tuple(
                file_change
                for file_change in commit_with_files.file_changes
                if not self._file_filter_service.is_generated_file(file_change.file_path)
            )

            # Create filtered commit with files
            filtered_commit_with_files = CommitWithFiles(
                hash=commit_with_files.hash,
                author=commit_with_files.author,
                date=commit_with_files.date,
                message=commit_with_files.message,
                file_changes=filtered_file_changes,
            )

            # Fetch diff content
            commit_diff = self._git_service.get_commit_diff_content(repo_path, commit_hash)

            # Check if diff is too large
            diff_size = len(commit_diff.diff_content)
            is_diff_too_large = diff_size > self._diff_size_config.max_diff_size

            if is_diff_too_large:
                # Use tool calling approach
                return self._summarize_with_tools(
                    repo_path, commit_hash, filtered_commit_with_files
                )
            else:
                # Use standard approach
                input_data = CommitSummaryInput(
                    commit=filtered_commit_with_files,
                    diff=commit_diff,
                )
                summary = self._llm_agent.summarize_commit(input_data)
                return summary

        except Exception as e:
            raise RuntimeError(f"Failed to summarize commit {commit_hash}: {str(e)}") from e

    def summarize_diff(self, commit_a_hash: str, commit_b_hash: str, diff: CommitDiff) -> str:
        """
        Generate a markdown summary for a diff between two commits.

        Args:
            commit_a_hash: Hash of the older commit
            commit_b_hash: Hash of the newer commit
            diff: CommitDiff containing the diff content

        Returns:
            Markdown-formatted summary of the diff

        Raises:
            RuntimeError: If summarization fails
        """
        try:
            input_data = DiffSummaryInput(
                commit_a_hash=commit_a_hash,
                commit_b_hash=commit_b_hash,
                diff=diff,
            )

            # Check if diff is too large
            diff_size = len(diff.diff_content)
            is_diff_too_large = diff_size > self._diff_size_config.max_diff_size

            if is_diff_too_large:
                # For large diffs, we could implement tool calling if needed
                # For now, we'll use a truncated version
                truncated_diff = CommitDiff(
                    commit_hash=diff.commit_hash,
                    diff_content=diff.diff_content[: self._diff_size_config.max_diff_size]
                    + "\n\n[Diff truncated due to size]",
                )
                input_data = DiffSummaryInput(
                    commit_a_hash=commit_a_hash,
                    commit_b_hash=commit_b_hash,
                    diff=truncated_diff,
                )

            summary = self._llm_agent.summarize_diff(input_data)
            return summary

        except Exception as e:
            raise RuntimeError(
                f"Failed to summarize diff between {commit_a_hash} and {commit_b_hash}: {str(e)}"
            ) from e

    def _summarize_with_tools(
        self, repo_path: Path, commit_hash: str, commit_with_files: CommitWithFiles
    ) -> str:
        """
        Generate a summary using tool calling for large diffs.

        Args:
            repo_path: Path to the git repository
            commit_hash: Hash of the commit
            commit_with_files: Commit data with filtered file changes

        Returns:
            Markdown-formatted summary of the commit
        """
        # Create input data with empty diff (we'll use tools instead)
        empty_diff = CommitDiff(commit_hash=commit_hash, diff_content="")
        input_data = CommitSummaryInput(
            commit=commit_with_files,
            diff=empty_diff,
        )

        # Create callback function for getting file diffs
        def get_file_diff_callback(file_path: str) -> str:
            """Callback to get diff for a specific file."""
            return self._git_service.get_file_diff(repo_path, commit_hash, file_path)

        # Check if agent supports tool calling
        if hasattr(self._llm_agent, "summarize_commit_with_tools"):
            return self._llm_agent.summarize_commit_with_tools(input_data, get_file_diff_callback)
        else:
            # Fallback: use standard approach even if large
            # This should not happen with BaseLangChainAgent, but handle gracefully
            input_data_with_diff = CommitSummaryInput(
                commit=commit_with_files,
                diff=CommitDiff(
                    commit_hash=commit_hash,
                    diff_content="[Diff too large - truncated]",
                ),
            )
            return self._llm_agent.summarize_commit(input_data_with_diff)
