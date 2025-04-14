"""
Common utility functions for l-command.
"""

import sys
from pathlib import Path


def count_lines(file_path: Path) -> int:
    """Count the number of lines in a file.

    Args:
        file_path: Path to the file to count lines in.

    Returns:
        The number of lines in the file, or 0 if an error occurs.
    """
    try:
        with file_path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError as e:
        print(f"Error counting lines: {e}", file=sys.stderr)
        return 0
