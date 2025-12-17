"""Factory for creating LLM agent instances."""

import os
from pathlib import Path

from dotenv import load_dotenv

from gitlab_ticker.summarization.repositories.implementations import (
    LangChainClaudeAgent,
    LangChainOpenAIAgent,
)
from gitlab_ticker.summarization.repositories.interfaces import LLMAgentRepository


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


def create_llm_agent(model_name: str | None = None) -> LLMAgentRepository:
    """
    Create an LLM agent instance based on configuration.

    Args:
        model_name: Optional model name override. If not provided, uses
                   LLM_PROVIDER and model-specific env vars.

    Returns:
        LLM agent instance (Claude or OpenAI)

    Raises:
        ValueError: If LLM_PROVIDER is invalid or required API keys are missing
    """
    _load_env_file()

    provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

    if provider == "anthropic" or provider == "claude":
        return LangChainClaudeAgent(model_name=model_name)
    elif provider == "openai" or provider == "gpt":
        return LangChainOpenAIAgent(model_name=model_name)
    else:
        raise ValueError(
            f"Invalid LLM_PROVIDER: {provider}. "
            "Supported values: 'anthropic', 'claude', 'openai', 'gpt'"
        )
