"""Batch summarization service for processing multiple commits."""

from pathlib import Path

from gitlab_ticker.git.domain.entities import Commit
from gitlab_ticker.git.services.git_service import GitService
from gitlab_ticker.summarization.domain.value_objects import BatchProcessingInput
from gitlab_ticker.summarization.services.summarization_service import SummarizationService


class BatchSummarizationService:
    """Service for processing and summarizing multiple commits in batch."""

    def __init__(
        self,
        git_service: GitService,
        summarization_service: SummarizationService,
    ) -> None:
        """
        Initialize BatchSummarizationService.

        Args:
            git_service: Service for fetching git commit data
            summarization_service: Service for generating commit summaries
        """
        self._git_service = git_service
        self._summarization_service = summarization_service

    def process_commits_range(
        self,
        repo_path: Path,
        commit_a: str,
        commit_b: str,
        output_dir: Path,
        skip_empty_merges: bool = False,
    ) -> None:
        """
        Process commits between two hashes and save summaries to individual markdown files.

        Args:
            repo_path: Path to the git repository
            commit_a: Older commit hash (start of range)
            commit_b: Newer commit hash (end of range)
            output_dir: Path to the output directory where commits_summaries/ will be created
            skip_empty_merges: If True, skip merge commits that contain no file changes

        Raises:
            RuntimeError: If processing fails at any step
        """
        try:
            # List all commits in the range
            commits = self._git_service.list_commits_between(
                repo_path, commit_a, commit_b
            )

            if not commits:
                return

            # Filter out empty merge commits if requested
            if skip_empty_merges:
                filtered_commits: list[tuple[int, Commit]] = []
                for commit in commits:
                    if not self._git_service.is_empty_merge_commit(repo_path, commit.hash):
                        filtered_commits.append((len(filtered_commits) + 1, commit))
            else:
                filtered_commits = [(idx + 1, commit) for idx, commit in enumerate(commits)]

            if not filtered_commits:
                return

            # Create commits_summaries directory
            commits_dir = output_dir / "commits_summaries"
            commits_dir.mkdir(parents=True, exist_ok=True)

            # Process each commit and write individual files
            for sequence, commit in filtered_commits:
                try:
                    summary = self._summarization_service.summarize_commit(
                        repo_path, commit.hash
                    )
                    self._write_commit_summary_file(
                        commits_dir, sequence, commit.hash, summary
                    )
                except Exception as e:
                    # Continue processing other commits even if one fails
                    error_summary = (
                        f"**Error**: Failed to summarize commit {commit.hash}: {str(e)}"
                    )
                    self._write_commit_summary_file(
                        commits_dir, sequence, commit.hash, error_summary
                    )

        except Exception as e:
            raise RuntimeError(
                f"Failed to process commits range {commit_a}..{commit_b}: {str(e)}"
            ) from e

    def process_commits_range_with_input(
        self, input_data: BatchProcessingInput
    ) -> None:
        """
        Process commits range using BatchProcessingInput dataclass.

        Args:
            input_data: Batch processing parameters

        Raises:
            RuntimeError: If processing fails at any step
        """
        self.process_commits_range(
            input_data.repo_path,
            input_data.commit_a,
            input_data.commit_b,
            input_data.output_dir,
        )

    @staticmethod
    def _write_commit_summary_file(
        commits_dir: Path,
        sequence: int,
        commit_hash: str,
        summary: str,
    ) -> None:
        """
        Write a single commit summary to a markdown file.

        Args:
            commits_dir: Directory where commit summary files are stored
            sequence: Sequence number of the commit (1-based)
            commit_hash: Full hash of the commit
            summary: Markdown summary content for the commit
        """
        # Format filename: {sequence:04d}_{commit_hash[:8]}.md
        filename = f"{sequence:04d}_{commit_hash[:8]}.md"
        output_file = commits_dir / filename

        with output_file.open("w", encoding="utf-8") as f:
            f.write(summary)
            if not summary.endswith("\n"):
                f.write("\n")

