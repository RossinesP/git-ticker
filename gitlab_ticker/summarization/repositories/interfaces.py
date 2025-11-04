"""Repository interfaces for LLM summarization operations."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from gitlab_ticker.summarization.domain.value_objects import CommitSummaryInput


class LLMAgentRepository(ABC):
    """Interface for LLM-based commit summarization."""

    @abstractmethod
    def summarize_commit(self, input_data: CommitSummaryInput) -> str:
        """
        Generate a markdown summary of a commit.

        Args:
            input_data: Commit data including message, file changes, and diff

        Returns:
            Markdown-formatted summary of the commit
        """
        ...

    def summarize_commit_with_tools(
        self,
        input_data: CommitSummaryInput,
        get_file_diff_callback: Callable[[str], str],
    ) -> str:
        """
        Generate a markdown summary of a commit using tool calling for file diffs.

        Args:
            input_data: Commit data including message and file changes (diff may be empty)
            get_file_diff_callback: Callback function to get diff for a specific file path

        Returns:
            Markdown-formatted summary of the commit

        Note:
            This method has a default implementation that raises NotImplementedError.
            Subclasses should override it if they support tool calling.
        """
        raise NotImplementedError(
            "Tool calling not supported by this agent. "
            "Use summarize_commit instead or implement summarize_commit_with_tools."
        )

