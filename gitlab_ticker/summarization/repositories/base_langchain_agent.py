"""Base class for LangChain-based LLM agents."""

from abc import ABC
from typing import TYPE_CHECKING

from gitlab_ticker.summarization.domain.value_objects import CommitSummaryInput
from gitlab_ticker.summarization.repositories.interfaces import LLMAgentRepository

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


class BaseLangChainAgent(LLMAgentRepository, ABC):
    """Base class for LangChain-based commit summarization agents."""

    def __init__(self) -> None:
        """Initialize the base agent with common configuration."""
        self._system_prompt = self._create_system_prompt()
        self._llm: BaseChatModel  # Set by subclasses

    def summarize_commit(self, input_data: CommitSummaryInput) -> str:
        """
        Generate a markdown summary of a commit.

        Args:
            input_data: Commit data including message, file changes, and diff

        Returns:
            Markdown-formatted summary of the commit

        Raises:
            RuntimeError: If the LLM API call fails
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        try:
            human_message = self._format_commit_input(input_data)
            messages = [
                SystemMessage(content=self._system_prompt),
                HumanMessage(content=human_message),
            ]

            response = self._llm.invoke(messages)
            # Handle different response types
            content = response.content
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                # If content is a list, extract text from it
                return " ".join(
                    str(item) if isinstance(item, str) else str(item.get("text", ""))
                    for item in content
                )
            else:
                # Fallback: convert any other type to string
                return str(content)  # type: ignore[unreachable]
        except Exception as e:
            raise RuntimeError(f"Failed to generate commit summary: {str(e)}") from e

    @staticmethod
    def _create_system_prompt() -> str:
        """Create the system prompt for the LLM agent."""
        return """You are an expert software engineer analyzing git commits. \
Your role is to analyze commit information and generate intelligent, \
structured summaries in markdown format.

Your task:
1. Analyze the commit message, file changes, and diff content
2. Identify the feature, module, or component impacted by this change
3. Determine the type of change:
   - New feature: A new functionality or component is being added
   - Bug fix: A bug or issue is being corrected
   - Enhancement: An existing feature is being improved
   - Upgrade/Dependency: Version updates or dependency changes
   - Refactoring: Code restructuring without behavior changes
   - Minor change: Small updates, documentation, or trivial changes

4. Generate an appropriate summary:
   - For NEW FEATURES: Describe the architecture in broad strokes. \
Explain what the feature does, its main components, and how it \
integrates with the existing system.
   - For MINOR CHANGES (bug fixes, version upgrades, small fixes): \
Keep it very short and concise. Just identify what was fixed or updated.
   - For MAJOR CHANGES (large enhancements, significant refactoring): \
Provide more detail about the changes, their impact, and the rationale.

Output format:
- Use clean markdown formatting
- Start with a brief one-line summary
- Then provide details organized in sections if needed
- Use bullet points for clarity
- Be concise but informative
- Focus on the "what" and "why", not the "how" \
(unless it's a new feature architecture)
- Do not prompt for further questions or comments.

Remember: Adjust the level of detail based on the magnitude of the change."""

    @staticmethod
    def _format_commit_input(input_data: CommitSummaryInput) -> str:
        """Format commit data into a prompt for the LLM."""
        commit = input_data.commit
        diff = input_data.diff

        # Format file changes
        file_changes_list: list[str] = []
        for file_change in commit.file_changes:
            change_info = f"- {file_change.file_path} ({file_change.change_type.value})"
            if file_change.old_path:
                change_info += f" (from {file_change.old_path})"
            file_changes_list.append(change_info)

        file_changes_text = (
            "\n".join(file_changes_list)
            if file_changes_list
            else "No files changed"
        )

        # Format the prompt
        prompt = f"""Commit Information:

Commit Hash: {commit.hash}
Author: {commit.author}
Date: {commit.date.isoformat()}
Message: {commit.message}

Files Changed:
{file_changes_text}

Diff Content:
{diff.diff_content}

Please analyze this commit and generate a markdown summary following the instructions provided."""

        return prompt

