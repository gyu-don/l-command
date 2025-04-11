#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    """Execute the l command."""
    parser = argparse.ArgumentParser(description="Simple file and directory viewer")
    parser.add_argument(
        "path", nargs="?", default=".", help="Path to file or directory to display"
    )
    args = parser.parse_args()

    path = Path(args.path)

    # Check if path exists
    if not path.exists():
        print(f"Error: Path not found: {path}")
        return 1

    try:
        # If it's a directory
        if path.is_dir():
            subprocess.run(["ls", "-la", "--color=auto", str(path)])
        # If it's a file
        else:
            subprocess.run(["less", "-RFX", str(path)])
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
