"""Repository interfaces for LLM summarization operations."""

from abc import ABC, abstractmethod

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

