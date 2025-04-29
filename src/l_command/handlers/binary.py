"""
Handler for processing binary files.
"""

import logging
import os
import shutil
import subprocess
from pathlib import Path

from l_command.handlers.base import FileHandler

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
                    logger.debug(f"'file' command identified {path} as '{encoding}'.")
                    return True
                # Trust 'file' command for common text encodings
                if encoding in ["us-ascii", "utf-8", "iso-8859-1"]:
                    logger.debug(
                        f"'file' command identified {path} as '{encoding}', performing secondary content check."
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

        try:
            # Get terminal height
            terminal_height = os.get_terminal_size().lines
        except OSError:
            # Fallback if not running in a terminal (e.g., piped)
            terminal_height = float("inf")  # Always use direct output

        command = ["hexdump", "-C", str(path)]

        try:
            # First subprocess call to count lines
            # Use Popen to handle potentially large output without loading all into memory
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            line_count = 0
            # Read line by line to count without storing the whole output
            try:
                for _ in process.stdout:  # type: ignore
                    line_count += 1
            except Exception as e:
                # Handle potential decoding errors if output isn't standard text,
                # although hexdump should be fine
                logger.warning(f"Error reading hexdump output: {e}")
            finally:
                process.stdout.close()  # type: ignore
                process.wait()  # Wait for the process to finish

            # Second subprocess call to display content
            if line_count > terminal_height and shutil.which("less"):
                hexdump_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                less_process = None  # Initialize less_process
                try:
                    less_process = subprocess.Popen(
                        ["less", "-R"],
                        stdin=hexdump_process.stdout,  # Let less handle stdout directly
                    )
                    # Close hexdump's stdout to signal EOF to less
                    hexdump_process.stdout.close()
                    # Wait for less to finish *after* hexdump stdout is closed
                    less_process.wait()  # Wait for less to exit naturally
                except BrokenPipeError:  # less exited early (e.g., user pressed 'q')
                    pass  # Not an error
                finally:
                    # Ensure hexdump process is terminated if still running
                    if hexdump_process.poll() is None:  # Check if process is still running
                        hexdump_process.terminate()
                        hexdump_process.wait()  # Wait for termination

                # Check less exit status *after* the try block
                if less_process and less_process.poll() is not None:  # Check if less started and finished
                    less_exit_code = less_process.returncode
                    if less_exit_code != 0:
                        # Try to capture stderr if less errored, might be None
                        try:
                            _, less_stderr_bytes = less_process.communicate(timeout=0.1)
                            less_stderr_msg = less_stderr_bytes.decode(errors="ignore")
                            logger.error(f"less exited with code {less_exit_code}: {less_stderr_msg}")
                        except subprocess.TimeoutExpired:
                            logger.error(f"less exited with code {less_exit_code} (stderr not captured)")
                        except Exception as e_comm:
                            logger.error(f"less exited with code {less_exit_code}, error capturing stderr: {e_comm}")
            else:
                # Output directly if it fits or less is not available
                # Using Popen/communicate to avoid loading large files entirely into memory
                try:
                    direct_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout_bytes, stderr_bytes = direct_process.communicate()
                    if direct_process.returncode == 0:
                        print(stdout_bytes.decode(errors="ignore"), end="")
                    else:
                        stderr_msg = stderr_bytes.decode(errors="ignore")
                        logger.error(f"hexdump exited with code {direct_process.returncode}: {stderr_msg}")
                except FileNotFoundError:
                    logger.error(f"Required command '{command[0]}' not found.")
                except Exception as e:
                    logger.exception(f"An unexpected error occurred running hexdump: {e}")

        except FileNotFoundError as e:
            if "hexdump" in str(e) or "less" in str(e):
                logger.error(f"Required command '{e.filename}' not found.")
            else:
                logger.error(f"Error accessing binary file: {e}")
        except subprocess.CalledProcessError as e:
            # Log errors from the hexdump command itself (should be rare with pipe)
            logger.error(f"Error running hexdump command: {e}")
            if e.stderr:
                logger.error(f"Hexdump stderr: {e.stderr.decode(errors='ignore')}")
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
