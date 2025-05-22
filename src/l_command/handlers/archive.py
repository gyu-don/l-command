"""
Handler for processing archive files such as ZIP and TAR formats.
"""

import logging
import shutil
import subprocess
from pathlib import Path

from l_command.handlers.base import FileHandler
from l_command.utils import smart_pager

logger = logging.getLogger(__name__)


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
            if suffix == ".zip" or suffix in [".jar", ".war", ".ear", ".apk", ".ipa"]:
                # Start unzip process
                unzip_process = subprocess.Popen(
                    ["unzip", "-l", str(path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # Use smart_pager to handle the output
                smart_pager(unzip_process, ["less", "-R"])

                # Check if unzip process failed
                unzip_retcode = unzip_process.wait()
                if unzip_retcode != 0:
                    logger.error(f"unzip process exited with code {unzip_retcode}")
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

                # Start tar process
                tar_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                # Use smart_pager to handle the output
                smart_pager(tar_process, ["less", "-R"])

                # Check if tar process failed
                tar_retcode = tar_process.wait()
                if tar_retcode != 0:
                    logger.error(f"tar process exited with code {tar_retcode}")
                return

        except subprocess.SubprocessError as e:
            logger.error(f"Error displaying archive: {e}")
        except OSError as e:
            logger.error(f"Error accessing archive file: {e}")

    @staticmethod
    def priority() -> int:
        """Return the priority of this handler."""
        return 80
