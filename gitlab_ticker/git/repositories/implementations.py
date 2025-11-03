"""Concrete implementation of Git repository operations."""

import subprocess
from pathlib import Path

from gitlab_ticker.git.domain.entities import Commit, CommitWithFiles
from gitlab_ticker.git.domain.value_objects import (
    CommitDiff,
    CommitRange,
    FileChange,
    FileChangeType,
)
from gitlab_ticker.git.repositories.interfaces import GitRepository


class GitRepositoryImpl(GitRepository):
    """Concrete implementation of Git repository operations using git commands."""

    def list_commits(self, commit_range: CommitRange) -> tuple[Commit, ...]:
        """
        List commits between two commit hashes.

        Args:
            commit_range: Range of commits to retrieve

        Returns:
            Tuple of commits ordered from oldest to newest
        """
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--format=%H|%an|%ai|%s",
                    f"{commit_range.commit_a}..{commit_range.commit_b}",
                ],
                cwd=commit_range.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            commits: list[Commit] = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("|", 3)
                if len(parts) == 4:
                    commit_hash, author, date_str, message = parts
                    from datetime import datetime

                    commit_date = datetime.fromisoformat(date_str.replace(" ", "T"))
                    commits.append(
                        Commit(
                            hash=commit_hash,
                            author=author,
                            date=commit_date,
                            message=message,
                        )
                    )

            return tuple(commits)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to list commits: {e.stderr.decode() if e.stderr else str(e)}"
            ) from e

    def list_file_changes(self, repo_path: Path, commit_hash: str) -> CommitWithFiles:
        """
        List files modified and their change types for a specific commit.

        Args:
            repo_path: Path to the git repository
            commit_hash: Hash of the commit

        Returns:
            CommitWithFiles containing commit information and file changes
        """
        try:
            # Get commit info
            commit_info_result = subprocess.run(
                ["git", "log", "-1", "--format=%H|%an|%ai|%s", commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            commit_line = commit_info_result.stdout.strip()
            if not commit_line:
                raise ValueError(f"Commit {commit_hash} not found")

            parts = commit_line.split("|", 3)
            if len(parts) != 4:
                raise ValueError(f"Invalid commit format: {commit_line}")

            commit_hash_parsed, author, date_str, message = parts
            from datetime import datetime

            commit_date = datetime.fromisoformat(date_str.replace(" ", "T"))

            # Get file changes
            file_changes_result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-status", "-r", commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )

            file_changes: list[FileChange] = []
            for line in file_changes_result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) == 2:
                    status, file_path = parts
                    change_type = self._parse_status_to_change_type(status)
                    file_changes.append(
                        FileChange(
                            file_path=file_path,
                            change_type=change_type,
                            old_path=None,
                        )
                    )
                elif len(parts) >= 3:  # Renamed or copied files
                    status, old_path, new_path = parts[0], parts[1], parts[2]
                    change_type = self._parse_status_to_change_type(status)
                    file_changes.append(
                        FileChange(
                            file_path=new_path,
                            change_type=change_type,
                            old_path=old_path,
                        )
                    )

            return CommitWithFiles(
                hash=commit_hash_parsed,
                author=author,
                date=commit_date,
                message=message,
                file_changes=tuple(file_changes),
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to list file changes: {e.stderr.decode() if e.stderr else str(e)}"
            ) from e

    def get_commit_diff(self, repo_path: Path, commit_hash: str) -> CommitDiff:
        """
        Get the diff content for a specific commit.

        Args:
            repo_path: Path to the git repository
            commit_hash: Hash of the commit

        Returns:
            CommitDiff containing the diff content
        """
        try:
            result = subprocess.run(
                ["git", "show", commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return CommitDiff(commit_hash=commit_hash, diff_content=result.stdout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to get commit diff: {e.stderr.decode() if e.stderr else str(e)}"
            ) from e

    @staticmethod
    def _parse_status_to_change_type(status: str) -> FileChangeType:
        """Parse git status code to FileChangeType."""
        status_code = status[0] if status else ""
        match status_code:
            case "A":
                return FileChangeType.ADDED
            case "M":
                return FileChangeType.MODIFIED
            case "D":
                return FileChangeType.DELETED
            case "R":
                return FileChangeType.RENAMED
            case "C":
                return FileChangeType.COPIED
            case _:
                return FileChangeType.MODIFIED  # Default fallback

