#!/usr/bin/env python3
"""
Script to validate git repository parameters and generate commit summaries:
- Repository path
- Branch name
- Commit A hash
- Commit B hash (optional, defaults to latest commit on branch)
- Output file (optional, defaults to commit_summaries.md)
"""

import argparse
import subprocess
import sys
from pathlib import Path

from gitlab_ticker.git.repositories.implementations import GitRepositoryImpl
from gitlab_ticker.git.services.git_service import GitService
from gitlab_ticker.summarization.repositories.factory import create_llm_agent
from gitlab_ticker.summarization.services.batch_summarization_service import (
    BatchSummarizationService,
)
from gitlab_ticker.summarization.services.summarization_service import (
    SummarizationService,
)


def is_git_repository(repo_path: Path) -> bool:
    """Check if the given path is a git repository."""
    git_dir = repo_path / ".git"
    return git_dir.exists() and git_dir.is_dir()


def branch_exists(repo_path: Path, branch_name: str) -> bool:
    """Check if the branch exists in the repository."""
    try:
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def commit_exists(repo_path: Path, commit_hash: str) -> bool:
    """Check if the commit exists in the repository."""
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", commit_hash],
            cwd=repo_path,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def get_latest_commit(repo_path: Path, branch_name: str) -> str | None:
    """Get the latest commit hash of the specified branch."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", branch_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def is_commit_ancestor(repo_path: Path, commit_a: str, commit_b: str) -> bool:
    """Check if commit A is an ancestor of commit B (i.e., B is more recent than A)."""
    try:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit_a, commit_b],
            cwd=repo_path,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def validate_parameters(
    repo_path: Path,
    branch_name: str,
    commit_a: str,
    commit_b: str | None,
) -> tuple[bool, str]:
    """
    Validate all parameters and return (is_valid, error_message).

    Args:
        repo_path: Path to the git repository
        branch_name: Name of the branch
        commit_a: Hash of commit A
        commit_b: Hash of commit B (None if not provided)

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate repository path
    if not repo_path.exists():
        return False, f"Repository path does not exist: {repo_path}"

    if not repo_path.is_dir():
        return False, f"Repository path is not a directory: {repo_path}"

    if not is_git_repository(repo_path):
        return False, f"Path is not a git repository: {repo_path}"

    # Validate branch
    if not branch_exists(repo_path, branch_name):
        return False, f"Branch '{branch_name}' does not exist in the repository"

    # Validate commit A
    if not commit_exists(repo_path, commit_a):
        return False, f"Commit A '{commit_a}' does not exist in the repository"

    # Get commit B (default to latest commit on branch if not provided)
    if commit_b is None:
        commit_b = get_latest_commit(repo_path, branch_name)
        if commit_b is None:
            return False, f"Could not get latest commit for branch '{branch_name}'"

    # Validate commit B
    if not commit_exists(repo_path, commit_b):
        return False, f"Commit B '{commit_b}' does not exist in the repository"

    # Validate that B is more recent than A
    if not is_commit_ancestor(repo_path, commit_a, commit_b):
        return False, (
            f"Commit B '{commit_b}' is not more recent than commit A '{commit_a}'. "
            f"B must be a descendant of A."
        )

    return True, "All parameters are valid"


def main() -> None:
    """Main function to parse arguments, validate parameters, and generate summaries."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate git repository parameters and generate commit summaries "
            "using AI-powered analysis"
        )
    )
    parser.add_argument(
        "repo_path",
        type=Path,
        help="Path to the git repository directory",
    )
    parser.add_argument(
        "branch_name",
        type=str,
        help="Name of the branch",
    )
    parser.add_argument(
        "commit_a",
        type=str,
        help="Hash of commit A (older commit)",
    )
    parser.add_argument(
        "commit_b",
        type=str,
        nargs="?",
        default=None,
        help="Hash of commit B (newer commit, defaults to latest commit on branch)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("commit_summaries.md"),
        help="Output markdown file path (default: commit_summaries.md)",
    )
    parser.add_argument(
        "--skip-summarization",
        action="store_true",
        help="Skip summarization and only validate parameters",
    )

    args = parser.parse_args()

    # Validate parameters
    is_valid, message = validate_parameters(
        args.repo_path,
        args.branch_name,
        args.commit_a,
        args.commit_b,
    )

    if not is_valid:
        print(f"✗ Validation failed: {message}", file=sys.stderr)
        sys.exit(1)

    print(f"✓ {message}")
    if args.commit_b is None:
        commit_b = get_latest_commit(args.repo_path, args.branch_name)
        if commit_b is None:
            print(
                "✗ Could not get latest commit for summarization",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"  Using latest commit on branch '{args.branch_name}': {commit_b}")
    else:
        commit_b = args.commit_b

    # Generate summaries if not skipped
    if not args.skip_summarization:
        try:
            print("\n📝 Generating commit summaries...")
            print(f"   Processing commits from {args.commit_a[:8]} to {commit_b[:8]}")

            # Initialize services
            git_repo = GitRepositoryImpl()
            git_service = GitService(git_repo)
            llm_agent = create_llm_agent()
            summarization_service = SummarizationService(git_service, llm_agent)
            batch_service = BatchSummarizationService(git_service, summarization_service)

            # Process commits and generate summaries
            batch_service.process_commits_range(
                repo_path=args.repo_path,
                commit_a=args.commit_a,
                commit_b=commit_b,
                output_file=args.output,
            )

            print("✓ Summaries generated successfully!")
            print(f"  Output file: {args.output.absolute()}")
            sys.exit(0)

        except ValueError as e:
            print(f"✗ Configuration error: {e}", file=sys.stderr)
            print(
                "  Hint: Set ANTHROPIC_API_KEY in .env file or environment",
                file=sys.stderr,
            )
            sys.exit(1)
        except Exception as e:
            print(f"✗ Failed to generate summaries: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("  (Skipping summarization as requested)")
        sys.exit(0)


if __name__ == "__main__":
    main()

