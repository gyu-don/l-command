"""
Handler for processing binary files.
"""

import logging
import shutil
import subprocess
from pathlib import Path

from l_command.handlers.base import FileHandler
from l_command.utils import smart_pager

# Limit the size of binary files we attempt to process to avoid performance issues
MAX_BINARY_SIZE_BYTES = 10 * 1024 * 1024  # 10MB

logger = logging.getLogger(__name__)


class BinaryHandler(FileHandler):
    """Handler for binary files."""

    @staticmethod
    def _is_binary_content(file_path: Path) -> bool:
        """
        Fallback check if file command is not available or fails.
        """
        # Read a sample
        # Let's keep 8KB as a reasonable compromise
        sample_size = 8192
        try:
            with file_path.open("rb") as f:
                sample = f.read(sample_size)
        except OSError:
            # If we can't read, assume not binary for safety?
            # Or maybe True? Let's stick with False for now.
            return False

        if not sample:
            # Empty file is considered text
            return False

        # Simplified check: only check for null bytes
        return b"\x00" in sample

    @staticmethod
    def can_handle(path: Path) -> bool:
        """Determine if the file is likely binary and should be handled."""
        if not path.is_file():
            return False

        try:
            if path.stat().st_size > MAX_BINARY_SIZE_BYTES:
                return False
            # Optimization: Handle empty files as non-binary
            if path.stat().st_size == 0:
                return False
        except OSError:
            # If we can't get stats, assume we shouldn't handle it
            return False

        # Prefer using the 'file' command if available
        if shutil.which("file"):
            try:
                result = subprocess.run(
                    ["file", "--mime-encoding", "-b", str(path)],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=1,  # Add a timeout to prevent hangs
                )
                encoding = result.stdout.strip()
                # Treat 'binary' or 'unknown-*' as binary
                if encoding == "binary" or encoding.startswith("unknown-"):
                    logger.debug("'file' command identified %s as '%s'.", path, encoding)
                    return True
                # Trust 'file' command for common text encodings
                if encoding in ["us-ascii", "utf-8", "iso-8859-1"]:
                    logger.debug(
                        "'file' command identified %s as '%s', performing secondary content check.",
                        path,
                        encoding,
                    )
                    try:
                        return BinaryHandler._is_binary_content(path)
                    except Exception as e:
                        # Log the error during the fallback check
                        logger.warning(f"Fallback content check failed for {path}: {e!s}")
                        # If fallback fails, cautiously assume it's not binary?
                        return False
                # If 'file' reported something else, it might be text or binary.
                # Let's cautiously treat it as non-binary for now, but log it.
                # Alternatively, we could fall back to _is_binary_content here too.
                logger.debug(f"'file' command reported '{encoding}' for {path}, treating as non-binary.")
                return False
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, UnicodeDecodeError) as e:
                logger.warning(f"'file' command check failed for {path}: {e!s}, falling back to content check.")
                # Fallback to content check if 'file' command fails
                return BinaryHandler._is_binary_content(path)
        else:
            # Fallback to content check if 'file' command is not available
            return BinaryHandler._is_binary_content(path)

    @staticmethod
    def handle(path: Path) -> None:
        """Display the contents of a binary file using hexdump."""
        if not shutil.which("hexdump"):
            logger.error("Error: 'hexdump' command not found. Cannot display binary file.")
            # Consider adding a fallback to 'strings' or basic message here later?
            return

        command = ["hexdump", "-C", str(path)]

        try:
            # Start hexdump process
            hexdump_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Use smart_pager to handle the output
            smart_pager(hexdump_process, ["less", "-R"])

            # Check if hexdump process failed
            hexdump_retcode = hexdump_process.wait()
            if hexdump_retcode != 0:
                logger.error(f"hexdump process exited with code {hexdump_retcode}")

        except FileNotFoundError as e:
            if "hexdump" in str(e) or "less" in str(e):
                logger.error(f"Required command '{e.filename}' not found.")
            else:
                logger.error(f"Error accessing binary file: {e}")
        except subprocess.SubprocessError as e:
            # Log errors from the hexdump command itself
            logger.error(f"Error running hexdump command: {e}")
        except OSError as e:
            # General OS errors (permissions, etc.)
            logger.error(f"OS error processing binary file: {e}")
        except Exception as e:
            # Catchall for any other unexpected issues
            logger.exception(f"An unexpected error occurred processing {path}: {e}")

    @staticmethod
    def priority() -> int:
        """Return the priority of this handler."""
        # Lower priority than JSON (90) and Archive (80), higher than default (0)
        return 60
