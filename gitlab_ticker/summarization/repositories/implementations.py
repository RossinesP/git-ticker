"""Concrete implementations of LLM summarization using LangChain."""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from gitlab_ticker.summarization.repositories.base_langchain_agent import (
    BaseLangChainAgent,
)


def _load_env_file() -> None:
    """Load environment variables from .env file."""
    # Try to find .env file in project root (parent of gitlab_ticker package)
    project_root = Path(__file__).parent.parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Fallback: try current directory
        load_dotenv()


class LangChainClaudeAgent(BaseLangChainAgent):
    """LangChain implementation using Claude for commit summarization."""

    def __init__(self, model_name: str | None = None) -> None:
        """
        Initialize the Claude agent with API key from environment.

        Args:
            model_name: Optional model name override. Defaults to claude-3-5-sonnet-20241022
        """
        _load_env_file()

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Please set it in a .env file or as an environment variable. "
                "See .env.example for reference."
            )

        model = model_name or os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

        if not isinstance(model, str):
            raise ValueError("Model name must be a string")

        self._llm = ChatAnthropic(  # type: ignore[call-arg]
            model_name=model,
            temperature=0.3,  # Lower temperature for more consistent summaries
        )

        super().__init__()


class LangChainOpenAIAgent(BaseLangChainAgent):
    """LangChain implementation using OpenAI for commit summarization."""

    def __init__(self, model_name: str | None = None) -> None:
        """
        Initialize the OpenAI agent with API key from environment.

        Args:
            model_name: Optional model name override. Defaults to gpt-4-turbo-preview
        """
        _load_env_file()

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required. "
                "Please set it in a .env file or as an environment variable. "
                "See .env.example for reference."
            )

        model = model_name or os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

        if not isinstance(model, str):
            raise ValueError("Model name must be a string")

        self._llm = ChatOpenAI(  # type: ignore[call-arg]
            model_name=model,
            temperature=0.3,  # Lower temperature for more consistent summaries
        )

        super().__init__()
