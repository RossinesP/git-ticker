"""Value objects for Summarization domain."""

from dataclasses import dataclass
from pathlib import Path

from gitlab_ticker.git.domain.entities import CommitWithFiles
from gitlab_ticker.git.domain.value_objects import CommitDiff


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
    output_file: Path

