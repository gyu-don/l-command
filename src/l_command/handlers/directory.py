"""
Handler for processing directories.
"""

import os
import subprocess
import sys
from pathlib import Path

from l_command.handlers.base import FileHandler


class DirectoryHandler(FileHandler):
    """Handler for processing directories."""

    @classmethod
    def can_handle(cls: type["DirectoryHandler"], path: Path) -> bool:
        """Check if the path is a directory.

        Args:
            path: The path to check.

        Returns:
            True if the path is a directory, False otherwise.
        """
        return path.is_dir()

    @classmethod
    def handle(cls: type["DirectoryHandler"], path: Path) -> None:
        """Display directory contents using ls -la, with paging if needed.

        The choice between direct output and less is based on the output's line count
        and the terminal's height.

        Args:
            path: The directory path to display.
        """
        try:
            # Run ls and capture output
            ls_process = subprocess.Popen(
                ["ls", "-la", "--color=always", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Count lines in the output
            output_lines = ls_process.stdout.readlines() if ls_process.stdout else []
            line_count = len(output_lines)

            # Get terminal height
            try:
                terminal_height = os.get_terminal_size().lines
            except OSError:
                terminal_height = float("inf")  # Fallback if not running in a terminal

            # Use less if output is larger than terminal height
            if line_count > terminal_height:
                # Reset stdout position
                ls_process = subprocess.Popen(
                    ["ls", "-la", "--color=always", str(path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                if ls_process.stdout:
                    subprocess.run(
                        ["less", "-R"],  # -R preserves color codes
                        stdin=ls_process.stdout,
                        check=True,
                    )
                    ls_process.stdout.close()
                    # Check if ls process failed
                    ls_retcode = ls_process.wait()
                    if ls_retcode != 0:
                        print(
                            f"ls process exited with code {ls_retcode}",
                            file=sys.stderr,
                        )
            else:
                # For small directories, display directly
                subprocess.run(["ls", "-la", "--color=auto", str(path)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error displaying directory with ls: {e}", file=sys.stderr)
        except OSError as e:
            print(f"Error accessing directory: {e}", file=sys.stderr)

    @classmethod
    def priority(cls: type["DirectoryHandler"]) -> int:
        """Return the priority of the directory handler.

        Returns:
            100 (highest priority).
        """
        return 100  # Directory has highest priority
