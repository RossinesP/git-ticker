"""Value objects for Summarization domain."""

from dataclasses import dataclass
from pathlib import Path

from git_ticker.git.domain.entities import CommitWithFiles
from git_ticker.git.domain.value_objects import CommitDiff


@dataclass(frozen=True)
class CommitSummaryInput:
    """Input data for commit summarization."""

    commit: CommitWithFiles
    diff: CommitDiff


@dataclass(frozen=True)
class BatchProcessingInput:
    """Input data for batch commit processing."""

    repo_path: Path
    commit_a: str
    commit_b: str
    output_dir: Path


@dataclass(frozen=True)
class DiffSummaryInput:
    """Input data for diff summarization between two commits."""

    commit_a_hash: str
    commit_b_hash: str
    diff: CommitDiff
