"""Git domain entities."""

from dataclasses import dataclass
from datetime import datetime

from git_ticker.git.domain.value_objects import FileChange


@dataclass(frozen=True)
class Commit:
    """Commit entity."""

    hash: str
    author: str
    date: datetime
    message: str


@dataclass(frozen=True)
class CommitWithFiles:
    """Commit entity with file changes information."""

    hash: str
    author: str
    date: datetime
    message: str
    file_changes: tuple[FileChange, ...]
