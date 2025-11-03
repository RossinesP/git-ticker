"""Value objects for Git domain."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class FileChangeType(str, Enum):
    """Type of file change in a commit."""

    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    COPIED = "copied"


@dataclass(frozen=True)
class CommitRange:
    """Range of commits between two commit hashes."""

    repo_path: Path
    commit_a: str
    commit_b: str


@dataclass(frozen=True)
class CommitInfo:
    """Information about a commit."""

    hash: str
    author: str
    date: datetime
    message: str


@dataclass(frozen=True)
class FileChange:
    """Information about a file change in a commit."""

    file_path: str
    change_type: FileChangeType
    old_path: str | None = None  # For renamed/copied files


@dataclass(frozen=True)
class CommitDiff:
    """Diff information for a commit."""

    commit_hash: str
    diff_content: str

