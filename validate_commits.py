#!/usr/bin/env python3
"""
Script to validate git repository parameters and generate commit summaries:
- Repository path
- Branch name (main branch)
- Commit A hash (optional if --dev-branch is used)
- Commit B hash (optional, defaults to latest commit on branch)
- Output directory (optional, defaults to ./output)
- --dev-branch: Development branch name (optional, enables diff mode between branches)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from gitlab_ticker.git.domain.value_objects import DiffSizeConfig
from gitlab_ticker.git.repositories.implementations import GitRepositoryImpl
from gitlab_ticker.git.services.git_service import GitService
from gitlab_ticker.notifications.repositories.implementations import (
    SlackNotificationRepositoryImpl,
)
from gitlab_ticker.notifications.services.notification_service import (
    NotificationService,
)
from gitlab_ticker.summarization.repositories.factory import create_llm_agent
from gitlab_ticker.summarization.services.batch_summarization_service import (
    BatchSummarizationService,
)
from gitlab_ticker.summarization.services.summarization_service import (
    SummarizationService,
)


def _load_env_file() -> None:
    """Load environment variables from .env file."""
    # Try to find .env file in project root (parent of gitlab_ticker package)
    project_root = Path(__file__).parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Fallback: try current directory
        load_dotenv()


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
    commit_a: str | None,
    commit_b: str | None,
) -> tuple[bool, str]:
    """
    Validate all parameters and return (is_valid, error_message).

    Args:
        repo_path: Path to the git repository
        branch_name: Name of the branch
        commit_a: Hash of commit A (None if not provided)
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

    # If commit_a is None, we're in dev-branch mode, so skip commit validation
    if commit_a is None:
        return True, "All parameters are valid (dev-branch mode)"

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


def validate_dev_branch_parameters(
    repo_path: Path,
    main_branch: str,
    dev_branch: str,
) -> tuple[bool, str]:
    """
    Validate parameters for dev-branch mode and return (is_valid, error_message).

    Args:
        repo_path: Path to the git repository
        main_branch: Name of the main branch
        dev_branch: Name of the development branch

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

    # Validate main branch
    if not branch_exists(repo_path, main_branch):
        return False, f"Main branch '{main_branch}' does not exist in the repository"

    # Validate dev branch
    if not branch_exists(repo_path, dev_branch):
        return False, f"Development branch '{dev_branch}' does not exist in the repository"

    # Check that branches are different
    if main_branch == dev_branch:
        return False, "Main branch and development branch must be different"

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
        nargs="?",
        default=None,
        help="Hash of commit A (older commit, optional if --dev-branch is used)",
    )
    parser.add_argument(
        "commit_b",
        type=str,
        nargs="?",
        default=None,
        help="Hash of commit B (newer commit, defaults to latest commit on branch)",
    )
    parser.add_argument(
        "--dev-branch",
        type=str,
        default=None,
        help=(
            "Development branch name. When specified, summarizes all commits "
            "from the development branch that are not in the main branch. "
            "In this mode, commit_a and commit_b are not required."
        ),
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("./output"),
        help="Output directory path (default: ./output)",
    )
    parser.add_argument(
        "--skip-summarization",
        action="store_true",
        help="Skip summarization and only validate parameters",
    )
    parser.add_argument(
        "--skip-empty-merges",
        action="store_true",
        help="Skip merge commits that contain no file changes",
    )
    parser.add_argument(
        "--max-diff-size",
        type=int,
        default=50000,
        help="Maximum diff size in characters before using tool calling (default: 50000)",
    )
    parser.add_argument(
        "--send-to-slack",
        action="store_true",
        help="Send the summary to a Slack channel (only available in dev-branch mode)",
    )
    parser.add_argument(
        "--slack-channel",
        type=str,
        help="Slack channel name (required if --send-to-slack is set)",
    )

    args = parser.parse_args()

    # Check if we're in dev-branch mode
    if args.dev_branch is not None:
        # Dev-branch mode: validate branches
        if args.commit_a is not None:
            print(
                "✗ Error: --dev-branch cannot be used with commit_a. "
                "Use either --dev-branch or commit range mode.",
                file=sys.stderr,
            )
            sys.exit(1)

        is_valid, message = validate_dev_branch_parameters(
            args.repo_path,
            args.branch_name,
            args.dev_branch,
        )

        if not is_valid:
            print(f"✗ Validation failed: {message}", file=sys.stderr)
            sys.exit(1)

        print(f"✓ {message}")
        print(f"  Main branch: {args.branch_name}")
        print(f"  Development branch: {args.dev_branch}")

        # Generate summaries if not skipped
        if not args.skip_summarization:
            try:
                print("\n📝 Generating diff summary...")
                print(f"   Analyzing diff from {args.branch_name} to {args.dev_branch}")

                # Initialize services
                git_repo = GitRepositoryImpl()
                git_service = GitService(git_repo)
                llm_agent = create_llm_agent()
                diff_size_config = DiffSizeConfig(max_diff_size=args.max_diff_size)
                summarization_service = SummarizationService(
                    git_service, llm_agent, diff_size_config=diff_size_config
                )

                # Get the diff between merge base and dev branch head
                merge_base, dev_branch_head, diff = git_service.get_dev_branch_diff(
                    repo_path=args.repo_path,
                    main_branch=args.branch_name,
                    dev_branch=args.dev_branch,
                )

                print(f"   Merge base: {merge_base[:8]}")
                print(f"   Dev branch head: {dev_branch_head[:8]}")
                print("\n📄 Generating summary...\n")

                # Generate summary
                summary = summarization_service.summarize_diff(
                    commit_a_hash=merge_base,
                    commit_b_hash=dev_branch_head,
                    diff=diff,
                )

                # Display summary in console
                print("=" * 80)
                print("DIFF SUMMARY")
                print("=" * 80)
                print(summary)
                print("=" * 80)

                print("\n✓ Summary generated successfully!")

                # Send to Slack if requested
                if args.send_to_slack:
                    if not args.slack_channel:
                        print(
                            "\n✗ Error: --slack-channel is required when --send-to-slack is set",
                            file=sys.stderr,
                        )
                        sys.exit(1)

                    try:
                        print(f"\n📤 Sending summary to Slack channel #{args.slack_channel}...")

                        # Load environment variables
                        _load_env_file()

                        # Get Slack token from environment
                        slack_token = os.getenv("SLACK_TOKEN")
                        if not slack_token:
                            raise ValueError(
                                "SLACK_TOKEN environment variable is required. "
                                "Please set it in a .env file or as an environment variable. "
                                "Get your token from https://api.slack.com/apps"
                            )

                        slack_repo = SlackNotificationRepositoryImpl(token=slack_token)
                        notification_service = NotificationService(slack_repo)

                        notification_service.send_summary_to_slack(
                            summary=summary,
                            channel_name=args.slack_channel,
                        )

                        print(f"✓ Summary sent successfully to #{args.slack_channel}!")

                    except ValueError as e:
                        print(f"\n✗ Configuration error: {e}", file=sys.stderr)
                        print(
                            "  Hint: Set SLACK_TOKEN in .env file or environment",
                            file=sys.stderr,
                        )
                        sys.exit(1)
                    except RuntimeError as e:
                        print(f"\n✗ Failed to send to Slack: {e}", file=sys.stderr)
                        sys.exit(1)
                    except Exception as e:
                        print(f"\n✗ Unexpected error sending to Slack: {e}", file=sys.stderr)
                        sys.exit(1)

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
    else:
        # Commit range mode: validate commits
        if args.commit_a is None:
            print(
                "✗ Error: commit_a is required when --dev-branch is not specified.",
                file=sys.stderr,
            )
            sys.exit(1)

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

        # Ensure commit_b is not None for type checking
        assert commit_b is not None, "commit_b must be set at this point"

        # Generate summaries if not skipped
        if not args.skip_summarization:
            try:
                print("\n📝 Generating commit summaries...")
                print(f"   Processing commits from {args.commit_a[:8]} to {commit_b[:8]}")

                # Initialize services
                git_repo = GitRepositoryImpl()
                git_service = GitService(git_repo)
                llm_agent = create_llm_agent()
                diff_size_config = DiffSizeConfig(max_diff_size=args.max_diff_size)
                summarization_service = SummarizationService(
                    git_service, llm_agent, diff_size_config=diff_size_config
                )
                batch_service = BatchSummarizationService(git_service, summarization_service)

                # Process commits and generate summaries
                batch_service.process_commits_range(
                    repo_path=args.repo_path,
                    commit_a=args.commit_a,
                    commit_b=commit_b,
                    output_dir=args.output,
                    skip_empty_merges=args.skip_empty_merges,
                )

                print("✓ Summaries generated successfully!")
                print(f"  Output directory: {args.output.absolute()}")
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
