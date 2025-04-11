#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys


def main() -> int:
    """Execute the l command."""
    parser = argparse.ArgumentParser(description="Simple file and directory viewer")
    parser.add_argument(
        "path", nargs="?", default=".", help="Path to file or directory to display"
    )
    args = parser.parse_args()

    path = args.path

    # Check if path exists
    if not os.path.exists(path):
        print(f"Error: Path not found: {path}")
        return 1

    try:
        # If it's a directory
        if os.path.isdir(path):
            subprocess.run(["ls", "-la", path])
        # If it's a file
        else:
            subprocess.run(["less", path])
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
