"""
Common utility functions for l-command.
"""

import os
import shutil
import subprocess
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


def smart_pager(
    content: subprocess.Popen | Path,
    pager_cmd: list[str] | None = None,
) -> None:
    """Display content with a pager if it exceeds terminal height.

    This function implements the "buffer and switch" approach:
    1. If stdout is not a TTY, output directly
    2. Buffer lines until they exceed terminal height
    3. If threshold is exceeded, switch to pager
    4. Otherwise, output directly

    Args:
        content: Content to display. Can be:
            - A subprocess.Popen object with stdout
            - A Path object (file will be read)
        pager_cmd: Pager command to use. Defaults to ["less", "-RFX"]
    """
    # Default pager command
    if pager_cmd is None:
        pager_cmd = ["less", "-RFX"]

    # If stdout is not a TTY, output directly without paging
    if not sys.stdout.isatty():
        if isinstance(content, subprocess.Popen):
            if content.stdout:
                shutil.copyfileobj(content.stdout, sys.stdout.buffer)
        elif isinstance(content, Path):
            try:
                with content.open("rb") as f:
                    shutil.copyfileobj(f, sys.stdout.buffer)
            except OSError as e:
                print(f"Error reading file: {e}", file=sys.stderr)
        return

    # Get terminal height
    try:
        terminal_height = os.get_terminal_size().lines
    except OSError:
        terminal_height = float("inf")  # Fallback if not in a terminal

    # Handle different content types
    if isinstance(content, subprocess.Popen):
        _handle_process_with_pager(content, terminal_height, pager_cmd)
    elif isinstance(content, Path):
        _handle_file_with_pager(content, terminal_height, pager_cmd)


def _handle_process_with_pager(
    process: subprocess.Popen,
    terminal_height: int | float,
    pager_cmd: list[str],
) -> None:
    """Handle subprocess output with pager if needed.

    Args:
        process: Subprocess with stdout to read from
        terminal_height: Terminal height in lines
        pager_cmd: Pager command to use
    """
    if not process.stdout:
        return

    # Buffer lines until threshold is reached
    buf: list[bytes] = []

    for i, line in enumerate(iter(process.stdout.readline, b""), 1):
        buf.append(line)
        if i > terminal_height:
            # Start pager and send buffered content
            pager_process = subprocess.Popen(
                pager_cmd,
                stdin=subprocess.PIPE,
            )
            if pager_process.stdin:
                for buffered_line in buf:
                    pager_process.stdin.write(buffered_line)

                # Continue reading from process and writing to pager
                shutil.copyfileobj(process.stdout, pager_process.stdin)
                pager_process.stdin.close()
                pager_process.wait()
                return

    # If we get here, output was smaller than terminal height
    # Write buffered content directly to stdout
    for line in buf:
        sys.stdout.buffer.write(line)
    sys.stdout.buffer.flush()


def _handle_file_with_pager(
    file_path: Path,
    terminal_height: int | float,
    pager_cmd: list[str],
) -> None:
    """Handle file content with pager if needed.

    Args:
        file_path: Path to file to read
        terminal_height: Terminal height in lines
        pager_cmd: Pager command to use
    """
    try:
        # For files, we can check line count first
        line_count = count_lines(file_path)

        if line_count > terminal_height:
            # Use pager for large files
            subprocess.run([*pager_cmd, str(file_path)], check=True)
        else:
            # Use cat for small files
            subprocess.run(["cat", str(file_path)], check=True)
    except OSError as e:
        print(f"Error accessing file: {e}", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error displaying file: {e}", file=sys.stderr)
