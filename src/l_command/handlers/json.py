"""
Handler for processing JSON files.
"""

import os
import subprocess
import sys
from pathlib import Path

from l_command.constants import (
    JSON_CONTENT_CHECK_BYTES,
    MAX_JSON_SIZE_BYTES,
)
from l_command.handlers.base import FileHandler
from l_command.utils import count_lines


class JsonHandler(FileHandler):
    """Handler for processing JSON files."""

    @classmethod
    def can_handle(cls: type["JsonHandler"], path: Path) -> bool:
        """Check if the path is a JSON file.

        Args:
            path: The path to check.

        Returns:
            True if the path is a JSON file, False otherwise.
        """
        if not path.is_file():
            return False

        # Check by extension
        if path.suffix.lower() == ".json":
            try:
                if path.stat().st_size == 0:
                    return False
            except OSError:
                return False  # Cannot stat, likely doesn't exist or permission error
            return True

        # Check by content
        try:
            with path.open("rb") as f:
                content_start = f.read(JSON_CONTENT_CHECK_BYTES)
                if not content_start:
                    return False
                try:
                    content_text = content_start.decode("utf-8").strip()
                    if content_text.startswith(("{", "[")):
                        return True
                except UnicodeDecodeError:
                    pass
        except OSError:
            pass

        return False

    @classmethod
    def handle(cls: type["JsonHandler"], path: Path) -> None:
        """Display JSON file using jq with fallbacks.

        Args:
            path: The JSON file path to display.
        """
        try:
            file_size = path.stat().st_size
            if file_size == 0:
                # jq empty fails on empty files, treat as non-JSON for display
                print("(Empty file)")  # Indicate it is empty
                return

            if file_size > MAX_JSON_SIZE_BYTES:
                print(
                    f"File size ({file_size} bytes) exceeds limit "
                    f"({MAX_JSON_SIZE_BYTES} bytes). "
                    f"Falling back to default viewer.",
                    file=sys.stderr,
                )
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Validate JSON using jq empty
            try:
                subprocess.run(
                    ["jq", "empty", str(path)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                print(
                    "jq command not found. Falling back to default viewer.",
                    file=sys.stderr,
                )
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return
            except subprocess.CalledProcessError:
                print(
                    "File identified as JSON but failed validation or is invalid. "
                    "Falling back to default viewer.",
                    file=sys.stderr,
                )
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return
            except OSError as e:
                print(f"Error running jq empty: {e}", file=sys.stderr)
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Count lines to determine whether to use less
            line_count = count_lines(path)

            # Get terminal height (same as in display_file_default)
            try:
                terminal_height = os.get_terminal_size().lines
            except OSError:
                # Fallback if not running in a terminal (e.g., piped)
                terminal_height = float("inf")  # Always use direct output

            # If validation passes, display formatted JSON with jq
            try:
                if line_count > terminal_height:
                    # For JSON files taller than terminal, use less with color
                    jq_process = subprocess.Popen(
                        ["jq", "--color-output", ".", str(path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    subprocess.run(
                        ["less", "-R"],  # -R preserves color codes
                        stdin=jq_process.stdout,
                        check=True,
                    )
                    jq_process.stdout.close()
                    # Check if jq process failed
                    jq_retcode = jq_process.wait()
                    if jq_retcode != 0:
                        print(
                            f"jq process exited with code {jq_retcode}",
                            file=sys.stderr,
                        )
                        from l_command.handlers.default import DefaultFileHandler

                        DefaultFileHandler.handle(path)
                else:
                    # For small JSON files, display directly
                    subprocess.run(["jq", ".", str(path)], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error displaying JSON with jq: {e}", file=sys.stderr)
                # Fallback even if formatting fails after validation
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
            except OSError as e:
                print(f"Error running jq command: {e}", file=sys.stderr)
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)

        except OSError as e:
            print(
                f"Error accessing file stats for JSON processing: {e}",
                file=sys.stderr,
            )
            # Fallback if we can't even get the file size
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def priority(cls: type["JsonHandler"]) -> int:
        """Return the priority of the JSON handler.

        Returns:
            50 (medium priority, higher than default).
        """
        return 50  # JSON has higher priority than default
