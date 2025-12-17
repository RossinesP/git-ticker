"""Service for filtering generated files."""

import re
from pathlib import Path


class FileFilterService:
    """Service for detecting generated files."""

    # Extensions commonly associated with generated files
    GENERATED_EXTENSIONS: frozenset[str] = frozenset(
        {
            ".lock",
            ".min.js",
            ".bundle.js",
            ".pb",
            ".bin",
            ".pyc",
            ".class",
            ".o",
            ".so",
            ".dll",
            ".exe",
            ".jar",
            ".war",
            ".ear",
            ".whl",
            ".egg",
        }
    )

    # Path patterns that indicate generated files
    GENERATED_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"node_modules", re.IGNORECASE),
        re.compile(r"dist", re.IGNORECASE),
        re.compile(r"build", re.IGNORECASE),
        re.compile(r"target", re.IGNORECASE),
        re.compile(r"\.venv", re.IGNORECASE),
        re.compile(r"__pycache__", re.IGNORECASE),
        re.compile(r"\.gradle", re.IGNORECASE),
        re.compile(r"\.mvn", re.IGNORECASE),
        re.compile(r"\.idea", re.IGNORECASE),
        re.compile(r"\.vscode", re.IGNORECASE),
        re.compile(r"\.next", re.IGNORECASE),
        re.compile(r"\.nuxt", re.IGNORECASE),
        re.compile(r"out", re.IGNORECASE),
        re.compile(r"bin", re.IGNORECASE),
        re.compile(r"obj", re.IGNORECASE),
    )

    # Name patterns that indicate generated files
    GENERATED_NAME_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"generated", re.IGNORECASE),
        re.compile(r"auto", re.IGNORECASE),
        re.compile(r"compiled", re.IGNORECASE),
        re.compile(r"\.min\.", re.IGNORECASE),
        re.compile(r"\.bundle\.", re.IGNORECASE),
    )

    def is_generated_file(self, file_path: str) -> bool:
        """
        Check if a file is likely generated based on heuristics.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file is likely generated, False otherwise
        """
        path_obj = Path(file_path)

        # Check extension
        if path_obj.suffix in self.GENERATED_EXTENSIONS:
            return True

        # Check if any part of the path matches generated path patterns
        path_str = str(path_obj)
        for pattern in self.GENERATED_PATH_PATTERNS:
            if pattern.search(path_str):
                return True

        # Check filename for generated name patterns
        filename = path_obj.name
        for pattern in self.GENERATED_NAME_PATTERNS:
            if pattern.search(filename):
                return True

        return False
