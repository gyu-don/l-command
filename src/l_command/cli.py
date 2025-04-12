#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

from l_command.constants import (
    JSON_CONTENT_CHECK_BYTES,
    MAX_JSON_SIZE_BYTES,
)


def should_try_jq(file_path: Path) -> bool:
    """Determine if a file is likely JSON and should be processed with jq."""
    # Check by extension first
    if file_path.suffix.lower() == ".json":
        # Treat empty .json files (e.g., temp files in tests) as non-jq targets
        # to avoid errors with jq empty on empty input.
        try:
            if file_path.stat().st_size == 0:
                return False
        except OSError:
            return False  # Cannot stat, likely doesn't exist or permission error
        return True

    # Check by content if extension doesn't match
    try:
        with file_path.open("rb") as f:
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


def count_lines(file_path: Path) -> int:
    """Count the number of lines in a file."""
    try:
        with file_path.open("rb") as f:
            return sum(1 for _ in f)
    except OSError as e:
        print(f"Error counting lines: {e}", file=sys.stderr)
        return 0


def display_file_default(file_path: Path) -> None:
    """Display file content using cat or less.

    The choice between cat and less is based on the file's line count
    and the terminal's height.
    """
    line_count = count_lines(file_path)

    try:
        # Get terminal height
        terminal_height = os.get_terminal_size().lines
    except OSError:
        # Fallback if not running in a terminal (e.g., piped)
        terminal_height = float("inf")  # Effectively always use cat

    # Use less if the file has more lines than the terminal height, otherwise use cat
    command = ["less", "-RFX"] if line_count > terminal_height else ["cat"]

    try:
        subprocess.run([*command, str(file_path)], check=True)
    except FileNotFoundError:
        # Handle case where cat or less might be missing (highly unlikely)
        print(f"Error: Required command '{command[0]}' not found.", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        # This might happen if cat/less fails for some reason
        print(f"Error displaying file with {command[0]}: {e}", file=sys.stderr)
    except OSError as e:
        print(f"Error accessing file for default display: {e}", file=sys.stderr)


def display_json_with_jq(file_path: Path) -> None:
    """Attempt to display a JSON file using jq, with fallbacks."""
    try:
        file_size = file_path.stat().st_size
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
            display_file_default(file_path)
            return

        # Validate JSON using jq empty
        try:
            subprocess.run(
                ["jq", "empty", str(file_path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            print(
                "jq command not found. Falling back to default viewer.", file=sys.stderr
            )
            display_file_default(file_path)
            return
        except subprocess.CalledProcessError:
            print(
                "File identified as JSON but failed validation or is invalid. "
                "Falling back to default viewer.",
                file=sys.stderr,
            )
            display_file_default(file_path)
            return
        except OSError as e:
            print(f"Error running jq empty: {e}", file=sys.stderr)
            display_file_default(file_path)
            return

        # Check line count to determine whether to use less
        line_count = count_lines(file_path)

        # Get terminal height for comparison (same as in display_file_default)
        try:
            terminal_height = os.get_terminal_size().lines
        except OSError:
            # Fallback if not running in a terminal (e.g., piped)
            terminal_height = float("inf")  # Effectively always use direct output

        # If validation passes, display formatted JSON with jq
        try:
            if line_count > terminal_height:
                # For JSON files taller than terminal, use less with color
                jq_process = subprocess.Popen(
                    ["jq", "--color-output", ".", str(file_path)],
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
                    print(f"jq process exited with code {jq_retcode}", file=sys.stderr)
                    display_file_default(file_path)
            else:
                # For small JSON files, display directly
                subprocess.run(["jq", ".", str(file_path)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error displaying JSON with jq: {e}", file=sys.stderr)
            # Fallback even if formatting fails after validation
            display_file_default(file_path)
        except OSError as e:
            print(f"Error running jq command: {e}", file=sys.stderr)
            display_file_default(file_path)

    except OSError as e:
        print(f"Error accessing file stats for JSON processing: {e}", file=sys.stderr)
        # Fallback if we can't even get the file size
        display_file_default(file_path)


def main() -> int:
    """Execute the l command."""
    parser = argparse.ArgumentParser(description="Simple file and directory viewer")
    parser.add_argument(
        "path", nargs="?", default=".", help="Path to file or directory to display"
    )
    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path not found: {path}", file=sys.stderr)
        return 1

    try:
        if path.is_dir():
            subprocess.run(["ls", "-la", "--color=auto", str(path)])
        elif path.is_file():
            if should_try_jq(path):
                display_json_with_jq(path)
            else:
                display_file_default(path)
        else:
            # Handle other path types like sockets, fifos, etc.
            print(f"Path is not a file or directory: {path}", file=sys.stderr)
            # Optionally run ls -la to show what it is
            subprocess.run(["ls", "-lad", str(path)])

    except subprocess.CalledProcessError as e:
        # Catch errors from ls command
        print(f"Error executing command: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        # General unexpected errors during processing
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
