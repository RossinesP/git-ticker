"""Batch summarization service for processing multiple commits."""

from pathlib import Path

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
        output_file: Path,
    ) -> None:
        """
        Process commits between two hashes and save summaries to markdown file.

        Args:
            repo_path: Path to the git repository
            commit_a: Older commit hash (start of range)
            commit_b: Newer commit hash (end of range)
            output_file: Path to the output markdown file

        Raises:
            RuntimeError: If processing fails at any step
        """
        try:
            # List all commits in the range
            commits = self._git_service.list_commits_between(
                repo_path, commit_a, commit_b
            )

            if not commits:
                # Write empty file or header only
                self._write_markdown_file(output_file, [], repo_path, commit_a, commit_b)
                return

            # Process each commit and collect summaries
            summaries: list[tuple[str, str]] = []  # (commit_hash, summary)
            for commit in commits:
                try:
                    summary = self._summarization_service.summarize_commit(
                        repo_path, commit.hash
                    )
                    summaries.append((commit.hash, summary))
                except Exception as e:
                    # Continue processing other commits even if one fails
                    error_summary = (
                        f"**Error**: Failed to summarize commit {commit.hash}: {str(e)}"
                    )
                    summaries.append((commit.hash, error_summary))

            # Write all summaries to markdown file
            self._write_markdown_file(output_file, summaries, repo_path, commit_a, commit_b)

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
            input_data.output_file,
        )

    @staticmethod
    def _write_markdown_file(
        output_file: Path,
        summaries: list[tuple[str, str]],
        repo_path: Path,
        commit_a: str,
        commit_b: str,
    ) -> None:
        """
        Write commit summaries to a markdown file.

        Args:
            output_file: Path to the output markdown file
            summaries: List of (commit_hash, summary) tuples
            repo_path: Path to the repository (for header)
            commit_a: Start commit hash
            commit_b: End commit hash
        """
        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with output_file.open("w", encoding="utf-8") as f:
            # Write header
            f.write("# Commit Summaries\n\n")
            f.write(f"**Repository**: `{repo_path}`\n")
            f.write(f"**Commit Range**: `{commit_a}` .. `{commit_b}`\n")
            f.write(f"**Total Commits**: {len(summaries)}\n\n")
            f.write("---\n\n")

            # Write each commit summary
            for commit_hash, summary in summaries:
                f.write(f"## Commit {commit_hash[:8]}\n\n")
                f.write(f"**Full Hash**: `{commit_hash}`\n\n")
                f.write(summary)
                f.write("\n\n---\n\n")

