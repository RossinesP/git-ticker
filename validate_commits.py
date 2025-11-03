#!/usr/bin/env python3
"""
Script to validate git repository parameters:
- Repository path
- Branch name
- Commit A hash
- Commit B hash (optional, defaults to latest commit on branch)
"""

import argparse
import subprocess
import sys
from pathlib import Path


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
    """Main function to parse arguments and validate parameters."""
    parser = argparse.ArgumentParser(
        description="Validate git repository parameters for commit comparison"
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

    args = parser.parse_args()

    is_valid, message = validate_parameters(
        args.repo_path,
        args.branch_name,
        args.commit_a,
        args.commit_b,
    )

    if is_valid:
        print(f"✓ {message}")
        if args.commit_b is None:
            latest_commit = get_latest_commit(args.repo_path, args.branch_name)
            print(f"  Using latest commit on branch '{args.branch_name}': {latest_commit}")
        sys.exit(0)
    else:
        print(f"✗ Validation failed: {message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

