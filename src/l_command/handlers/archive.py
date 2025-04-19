"""
Handler for processing archive files such as ZIP and TAR formats.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from l_command.handlers.base import FileHandler


class ArchiveHandler(FileHandler):
    """Handler for archive files."""

    @staticmethod
    def can_handle(path: Path) -> bool:
        """Determine if the file is an archive that can be handled."""
        suffix = path.suffix.lower()
        name = path.name.lower()

        if suffix in (".zip", ".jar", ".war", ".ear", ".apk", ".ipa"):
            return shutil.which("unzip") is not None

        # Check required command for TAR archives:
        if shutil.which("tar") is not None:
            if name.endswith(".tar.zst") and shutil.which("unzstd") is not None:
                return True
            if name.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz")):
                return True

        return False

    @staticmethod
    def handle(path: Path) -> None:
        """Display the contents of an archive file."""
        suffix = path.suffix.lower()
        name = path.name.lower()

        try:
            # Get terminal height
            terminal_height = os.get_terminal_size().lines
        except OSError:
            # Fallback if not running in a terminal (e.g., piped)
            terminal_height = float("inf")  # Always use direct output

        # Use less if output is taller than terminal height
        try:
            if suffix == ".zip" or suffix in [".jar", ".war", ".ear", ".apk", ".ipa"]:
                # First subprocess call to count lines
                process = subprocess.Popen(
                    ["unzip", "-l", str(path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                stdout, _ = process.communicate()
                line_count = stdout.decode("utf-8").count("\n")

                # Second subprocess call to display content
                if line_count > terminal_height:
                    unzip_process = subprocess.Popen(
                        ["unzip", "-l", str(path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    subprocess.run(["less", "-R"], stdin=unzip_process.stdout, check=True)
                    unzip_process.stdout.close()
                    unzip_retcode = unzip_process.wait()
                    if unzip_retcode != 0:
                        print(
                            f"unzip process exited with code {unzip_retcode}",
                            file=sys.stderr,
                        )
                else:
                    subprocess.run(["unzip", "-l", str(path)], check=True)
                return

            if suffix == ".tar" or name.endswith(
                (".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz", ".tar.zst")
            ):
                command = ["tar", "-tvf", str(path)]
                if name.endswith(".tar.zst"):
                    command = [
                        "tar",
                        "--use-compress-program=unzstd",
                        "-tvf",
                        str(path),
                    ]

                # First subprocess call to count lines
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, _ = process.communicate()
                line_count = stdout.decode("utf-8").count("\n")

                # Second subprocess call to display content
                if line_count > terminal_height:
                    tar_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    subprocess.run(["less", "-R"], stdin=tar_process.stdout, check=True)
                    tar_process.stdout.close()
                    tar_retcode = tar_process.wait()
                    if tar_retcode != 0:
                        print(
                            f"tar process exited with code {tar_retcode}",
                            file=sys.stderr,
                        )
                else:
                    subprocess.run(command, check=True)
                return

        except subprocess.CalledProcessError as e:
            print(f"Error displaying archive with less: {e}", file=sys.stderr)
        except OSError as e:
            print(f"Error accessing archive file: {e}", file=sys.stderr)

    @staticmethod
    def priority() -> int:
        """Return the priority of this handler."""
        return 80
