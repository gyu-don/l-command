#!/usr/bin/env python3
"""
CLI entry point for l-command
"""

import argparse
import subprocess
import sys
from pathlib import Path

from l_command.config import load_config
from l_command.handlers import get_handlers


def main() -> int:
    """Execute the l command.

    Returns:
        0 for success, 1 for error.
    """
    parser = argparse.ArgumentParser(description="Simple file and directory viewer")
    parser.add_argument("path", nargs="?", default=".", help="Path to file or directory to display")
    args = parser.parse_args()

    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path not found: {path}", file=sys.stderr)
        return 1

    try:
        # Load configuration
        config = load_config()

        # Find appropriate handler and delegate processing
        for handler_class in get_handlers(config):
            if handler_class.can_handle(path):
                handler_class.handle(path)
                break
        else:
            # Handle special path types (sockets, FIFOs, etc.)
            print(f"Path is not a file or directory: {path}", file=sys.stderr)
            # Run ls -lad to show what it is
            subprocess.run(["ls", "-lad", str(path)], check=False)

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
