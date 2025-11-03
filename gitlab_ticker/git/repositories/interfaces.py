"""Repository interfaces for Git operations."""

from abc import ABC, abstractmethod
from pathlib import Path

from gitlab_ticker.git.domain.entities import Commit, CommitWithFiles
from gitlab_ticker.git.domain.value_objects import CommitDiff, CommitRange


class GitRepository(ABC):
    """Interface for Git repository operations."""

    @abstractmethod
    def list_commits(self, commit_range: CommitRange) -> tuple[Commit, ...]:
        """
        List commits between two commit hashes.

        Args:
            commit_range: Range of commits to retrieve

        Returns:
            Tuple of commits ordered from oldest to newest
        """
        ...

    @abstractmethod
    def list_file_changes(self, repo_path: Path, commit_hash: str) -> CommitWithFiles:
        """
        List files modified and their change types for a specific commit.

        Args:
            repo_path: Path to the git repository
            commit_hash: Hash of the commit

        Returns:
            CommitWithFiles containing commit information and file changes
        """
        ...

    @abstractmethod
    def get_commit_diff(self, repo_path: Path, commit_hash: str) -> CommitDiff:
        """
        Get the diff content for a specific commit.

        Args:
            repo_path: Path to the git repository
            commit_hash: Hash of the commit

        Returns:
            CommitDiff containing the diff content
        """
        ...

