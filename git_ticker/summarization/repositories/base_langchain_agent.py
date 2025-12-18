"""Base class for LangChain-based LLM agents."""

from abc import ABC
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from git_ticker.summarization.domain.value_objects import (
    CommitSummaryInput,
    DiffSummaryInput,
)
from git_ticker.summarization.repositories.interfaces import LLMAgentRepository
from git_ticker.summarization.templates import DEFAULT_TEMPLATE_PATH

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
else:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import StructuredTool


class BaseLangChainAgent(LLMAgentRepository, ABC):
    """Base class for LangChain-based commit summarization agents."""

    def __init__(self, template_path: Path | None = None) -> None:
        """Initialize the base agent with common configuration.

        Args:
            template_path: Path to a custom summary template file.
                          Defaults to the built-in template.
        """
        self._template_path = template_path or DEFAULT_TEMPLATE_PATH
        self._output_format_template = self._load_output_format_template()
        self._system_prompt = self._create_system_prompt()
        self._llm: BaseChatModel  # Set by subclasses

    def _load_output_format_template(self) -> str:
        """Load the output format template from file.

        Returns:
            The content of the template file.

        Raises:
            FileNotFoundError: If the template file does not exist.
            RuntimeError: If the template file cannot be read.
        """
        try:
            return self._template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Summary template file not found: {self._template_path}"
            ) from None
        except Exception as e:
            raise RuntimeError(
                f"Failed to read summary template file: {self._template_path}: {e}"
            ) from e

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

        Raises:
            RuntimeError: If the LLM API call fails
        """
        try:
            # Create the tool for getting file diffs
            def get_file_diff_tool_func(file_path: str) -> str:
                """Get the diff content for a specific file."""
                return get_file_diff_callback(file_path)

            get_file_diff_tool = StructuredTool.from_function(
                func=get_file_diff_tool_func,
                name="get_file_diff",
                description="Get the diff content for a specific file in the commit. "
                "Use this tool to request the diff for any file from the files changed list "
                "when you need to analyze its changes in detail.",
            )

            # Bind tools to the LLM
            llm_with_tools = self._llm.bind_tools([get_file_diff_tool])

            # Format input with file list only (no full diff)
            human_message_content = self._format_commit_input_files_only(input_data)
            system_prompt = self._create_system_prompt_with_tools()

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_message_content),
            ]

            # Iterative tool calling loop
            max_iterations = 10  # Prevent infinite loops
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                response = llm_with_tools.invoke(messages)

                # Check if the model wants to call a tool
                tool_calls = getattr(response, "tool_calls", None) or []
                if tool_calls and len(tool_calls) > 0:
                    messages.append(response)

                    # Execute tool calls
                    for tool_call in tool_calls:
                        # Handle different tool_call formats
                        if isinstance(tool_call, dict):
                            tool_name = tool_call.get("name", "")
                            tool_args = tool_call.get("args", {})
                            tool_call_id = tool_call.get("id", "")
                        else:
                            # Handle tool_call as an object
                            tool_name = getattr(tool_call, "name", "")
                            tool_args = getattr(tool_call, "args", {})
                            tool_call_id = getattr(tool_call, "id", "")

                        if tool_name == "get_file_diff":
                            file_path = (
                                tool_args.get("file_path", "")
                                if isinstance(tool_args, dict)
                                else ""
                            )
                            try:
                                diff_content = get_file_diff_tool_func(file_path)
                                messages.append(
                                    ToolMessage(
                                        content=diff_content,
                                        tool_call_id=tool_call_id,
                                    )
                                )
                            except Exception as e:
                                messages.append(
                                    ToolMessage(
                                        content=f"Error getting diff for {file_path}: {str(e)}",
                                        tool_call_id=tool_call_id,
                                    )
                                )
                        else:
                            messages.append(
                                ToolMessage(
                                    content=f"Unknown tool: {tool_name}",
                                    tool_call_id=tool_call_id,
                                )
                            )
                else:
                    # No more tool calls, extract the final response
                    messages.append(response)
                    content = response.content
                    if isinstance(content, str):
                        return content
                    elif isinstance(content, list):
                        return " ".join(
                            str(item) if isinstance(item, str) else str(item.get("text", ""))
                            for item in content
                        )
                    else:
                        return str(content)  # type: ignore[unreachable]

            # If we exit the loop, return the last response
            last_message = messages[-1]
            if isinstance(last_message, AIMessage):
                content = last_message.content
                if isinstance(content, str):
                    return content
                elif isinstance(content, list):
                    return " ".join(
                        str(item) if isinstance(item, str) else str(item.get("text", ""))
                        for item in content
                    )
                else:
                    return str(content)  # type: ignore[unreachable]

            raise RuntimeError("Maximum iterations reached in tool calling loop")

        except Exception as e:
            raise RuntimeError(f"Failed to generate commit summary: {str(e)}") from e

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM agent."""
        return f"""You are an expert software engineer analyzing git commits. \
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

4. Generate a structured summary following the exact format below.

Output format:
{self._output_format_template}"""

    def _create_system_prompt_with_tools(self) -> str:
        """Create the system prompt for the LLM agent when using tools."""
        return f"""You are an expert software engineer analyzing git commits. \
Your role is to analyze commit information and generate intelligent, \
structured summaries in markdown format.

The commit diff is too large to include in full. You have been provided with \
a list of files changed. Use the get_file_diff tool to request the diff \
content for specific files that you need to analyze in detail. You should \
request diffs for the most important files that will help you understand \
the nature and impact of the changes.

Your task:
1. Review the list of files changed
2. Use the get_file_diff tool to request diffs for key files (prioritize source code files, \
configuration files, and files that seem most relevant based on the commit message)
3. Analyze the changes you've requested
4. Identify the feature, module, or component impacted by this change
5. Determine the type of change:
   - New feature: A new functionality or component is being added
   - Bug fix: A bug or issue is being corrected
   - Enhancement: An existing feature is being improved
   - Upgrade/Dependency: Version updates or dependency changes
   - Refactoring: Code restructuring without behavior changes
   - Minor change: Small updates, documentation, or trivial changes

6. Generate a structured summary following the exact format below.

Output format:
{self._output_format_template}

Remember: Request diffs for the most important files first, then generate your summary based on \
the changes you've examined. You don't need to request diffs for all files - focus on the ones \
most relevant to understanding the commit's purpose."""

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
            "\n".join(file_changes_list) if file_changes_list else "No files changed"
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

    def summarize_diff(self, input_data: DiffSummaryInput) -> str:
        """
        Generate a markdown summary of a diff between two commits.

        Args:
            input_data: Diff data including commit hashes and diff content

        Returns:
            Markdown-formatted summary of the diff

        Raises:
            RuntimeError: If the LLM API call fails
        """
        try:
            system_prompt = self._create_diff_system_prompt()
            human_message_content = self._format_diff_input(input_data)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_message_content),
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
            raise RuntimeError(f"Failed to generate diff summary: {str(e)}") from e

    def _create_diff_system_prompt(self) -> str:
        """Create the system prompt for diff summarization."""
        return f"""You are an expert software engineer analyzing git diffs. \
Your role is to analyze the diff between two commits and generate intelligent, \
structured summaries in markdown format.

Your task:
1. Analyze the diff content between the two commits
2. Identify the overall changes, features, or modifications
3. Determine the type of changes:
   - New feature: A new functionality or component is being added
   - Bug fix: A bug or issue is being corrected
   - Enhancement: An existing feature is being improved
   - Upgrade/Dependency: Version updates or dependency changes
   - Refactoring: Code restructuring without behavior changes
   - Minor change: Small updates, documentation, or trivial changes

4. Generate a structured summary following the exact format below.

Output format:
{self._output_format_template}"""

    @staticmethod
    def _format_diff_input(input_data: DiffSummaryInput) -> str:
        """Format diff data into a prompt for the LLM."""
        prompt = f"""Diff Information:

From commit: {input_data.commit_a_hash}
To commit: {input_data.commit_b_hash}

Diff Content:
{input_data.diff.diff_content}

Please analyze this diff and generate a markdown summary following the instructions provided."""

        return prompt

    @staticmethod
    def _format_commit_input_files_only(input_data: CommitSummaryInput) -> str:
        """Format commit data into a prompt for the LLM (files list only, no diff)."""
        commit = input_data.commit

        # Format file changes
        file_changes_list: list[str] = []
        for file_change in commit.file_changes:
            change_info = f"- {file_change.file_path} ({file_change.change_type.value})"
            if file_change.old_path:
                change_info += f" (from {file_change.old_path})"
            file_changes_list.append(change_info)

        file_changes_text = (
            "\n".join(file_changes_list) if file_changes_list else "No files changed"
        )

        # Format the prompt
        prompt = f"""Commit Information:

Commit Hash: {commit.hash}
Author: {commit.author}
Date: {commit.date.isoformat()}
Message: {commit.message}

Files Changed:
{file_changes_text}

Note: The full diff for this commit is too large to include. Use the get_file_diff tool \
to request the diff content for specific files you want to analyze. Focus on the most \
important files that will help you understand the nature and impact of this commit.

Please analyze this commit and generate a markdown summary following the instructions provided."""

        return prompt
