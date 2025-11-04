"""Git service for coordinating Git operations."""

import subprocess
from pathlib import Path

from gitlab_ticker.git.domain.entities import Commit, CommitWithFiles
from gitlab_ticker.git.domain.value_objects import CommitDiff, CommitRange
from gitlab_ticker.git.repositories.interfaces import GitRepository


class GitService:
    """Service for Git operations."""

    def __init__(self, git_repository: GitRepository) -> None:
        """
        Initialize GitService.

        Args:
            git_repository: Repository implementation for Git operations
        """
        self._git_repository = git_repository

    def list_commits_between(
        self, repo_path: Path, commit_a: str, commit_b: str
    ) -> tuple[Commit, ...]:
        """
        List commits between two commit hashes.

        Args:
            repo_path: Path to the git repository
            commit_a: Older commit hash
            commit_b: Newer commit hash

        Returns:
            Tuple of commits ordered from oldest to newest
        """
        commit_range = CommitRange(
            repo_path=repo_path,
            commit_a=commit_a,
            commit_b=commit_b,
        )
        return self._git_repository.list_commits(commit_range)

    def list_file_changes_by_commit(self, repo_path: Path, commit_hash: str) -> CommitWithFiles:
        """
        List files modified and their change types for a specific commit.

        Args:
            repo_path: Path to the git repository
            commit_hash: Hash of the commit

        Returns:
            CommitWithFiles containing commit information and file changes
        """
        return self._git_repository.list_file_changes(repo_path, commit_hash)

    def get_commit_diff_content(self, repo_path: Path, commit_hash: str) -> CommitDiff:
        """
        Get the diff content for a specific commit.

        Args:
            repo_path: Path to the git repository
            commit_hash: Hash of the commit

        Returns:
            CommitDiff containing the diff content
        """
        return self._git_repository.get_commit_diff(repo_path, commit_hash)

    def get_file_diff(self, repo_path: Path, commit_hash: str, file_path: str) -> str:
        """
        Get the diff content for a specific file in a commit.

        Args:
            repo_path: Path to the git repository
            commit_hash: Hash of the commit
            file_path: Path to the file relative to repository root

        Returns:
            Diff content for the specific file
        """
        return self._git_repository.get_file_diff(repo_path, commit_hash, file_path)

    def is_empty_merge_commit(self, repo_path: Path, commit_hash: str) -> bool:
        """
        Check if a commit is a merge commit with no file changes.

        Args:
            repo_path: Path to the git repository
            commit_hash: Hash of the commit to check

        Returns:
            True if the commit is a merge commit with no file changes, False otherwise
        """
        try:
            # Get number of parents (merge commits have 2+ parents)
            result = subprocess.run(
                ["git", "log", "-1", "--format=%P", commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            parents = result.stdout.strip().split()
            is_merge_commit = len(parents) > 1

            if not is_merge_commit:
                return False

            # Check if there are any file changes
            commit_with_files = self.list_file_changes_by_commit(repo_path, commit_hash)
            has_no_changes = len(commit_with_files.file_changes) == 0

            return has_no_changes
        except subprocess.CalledProcessError:
            # If we can't check, assume it's not an empty merge
            return False

