"""
Handler for processing YAML files.
"""

import logging
import subprocess
from pathlib import Path

from l_command.handlers.base import FileHandler
from l_command.utils import smart_pager

# Constants specific to YAML handling
MAX_YAML_SIZE_BYTES = 50 * 1024 * 1024  # 50MB limit for YAML processing
YAML_CONTENT_CHECK_BYTES = 1024
SUPPORTED_YAML_EXTENSIONS = {".yaml", ".yml"}

logger = logging.getLogger(__name__)


class YAMLHandler(FileHandler):
    """Handler for processing YAML files."""

    @classmethod
    def can_handle(cls: type["YAMLHandler"], path: Path) -> bool:
        """Check if the path is a YAML file.

        Args:
            path: The path to check.

        Returns:
            True if the path is a YAML file, False otherwise.
        """
        if not path.is_file():
            return False

        # Check by extension
        if path.suffix.lower() in SUPPORTED_YAML_EXTENSIONS:
            try:
                if path.stat().st_size == 0:
                    return False
            except OSError:
                return False  # Cannot stat, likely doesn't exist or permission error
            return True

        # Check by content for files without extension
        try:
            with path.open("rb") as f:
                content_start = f.read(YAML_CONTENT_CHECK_BYTES)
                if not content_start:
                    return False
                try:
                    content_text = content_start.decode("utf-8").strip()
                    # Look for YAML document markers or common YAML patterns
                    if (
                        content_text.startswith("---")
                        or content_text.startswith("%YAML")
                        or cls._has_yaml_structure(content_text)
                    ):
                        return True
                except UnicodeDecodeError:
                    pass
        except OSError:
            pass

        return False

    @classmethod
    def _has_yaml_structure(cls: type["YAMLHandler"], content: str) -> bool:
        """Check if content has YAML-like structure.

        Args:
            content: The text content to check.

        Returns:
            True if content appears to be YAML, False otherwise.
        """
        lines = content.split("\n")[:10]  # Check first 10 lines
        yaml_indicators = 0

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Look for YAML patterns
            if (
                ":" in line
                and not line.startswith("{")
                and not line.startswith("[")
                and not line.endswith(",")
                and not line.endswith(";")
            ) or line.startswith("- "):
                yaml_indicators += 1
            elif line == "---" or line == "...":  # Document separators
                yaml_indicators += 2

        # Consider it YAML if we found multiple indicators
        return yaml_indicators >= 2

    @classmethod
    def handle(cls: type["YAMLHandler"], path: Path) -> None:
        """Display YAML file using yq with fallbacks.

        Args:
            path: The YAML file path to display.
        """
        try:
            file_size = path.stat().st_size
            if file_size == 0:
                print("(Empty YAML file)")
                return

            if file_size > MAX_YAML_SIZE_BYTES:
                logger.warning(
                    f"YAML file size ({file_size} bytes) exceeds limit "
                    f"({MAX_YAML_SIZE_BYTES} bytes). "
                    f"Falling back to default viewer.",
                )
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Try to use yq for formatting first
            if cls._try_yq_format(path):
                return

            # Try validation with yq
            if cls._try_yq_validate(path):
                return

            # Fallback to showing with syntax highlighting
            cls._show_yaml_source(path, file_size)

        except OSError as e:
            logger.error(
                f"Error accessing YAML file: {e}",
            )
            # Fallback if we can't even get the file size
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def _try_yq_format(cls: type["YAMLHandler"], path: Path) -> bool:
        """Try to format YAML using yq.

        Args:
            path: The YAML file path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Use yq to format and colorize YAML
            yq_process = subprocess.Popen(
                ["yq", "--colors", ".", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Use smart_pager to handle the output
            smart_pager(yq_process, ["less", "-R"])

            # Check if yq process failed
            yq_retcode = yq_process.wait()
            return yq_retcode == 0
        except FileNotFoundError:
            return False
        except subprocess.SubprocessError:
            return False

    @classmethod
    def _try_yq_validate(cls: type["YAMLHandler"], path: Path) -> bool:
        """Try to validate YAML using yq and show basic info.

        Args:
            path: The YAML file path.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Try to parse with yq for validation
            result = subprocess.run(
                ["yq", "length", str(path)],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print(f"YAML File: {path.name} (Valid)")
                try:
                    length = result.stdout.strip()
                    if length.isdigit():
                        print(f"Top-level items: {length}")
                except (ValueError, AttributeError):
                    pass
                print("-" * 50)
                # Show the original content since formatting failed
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return True
            else:
                print(f"YAML File: {path.name} (Validation errors)")
                if result.stderr:
                    print("Validation errors:")
                    print(result.stderr.strip())
                print("\nRaw content:")
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return True

        except subprocess.SubprocessError:
            return False

    @classmethod
    def _show_yaml_source(cls: type["YAMLHandler"], path: Path, file_size: int) -> None:
        """Show YAML file source with information.

        Args:
            path: The YAML file path.
            file_size: The file size in bytes.
        """
        print(f"YAML File: {path.name}")
        print(f"Size: {file_size:,} bytes")
        print("(Install 'yq' for YAML formatting and validation)")
        print("-" * 50)

        # Try to use bat for syntax highlighting, fallback to cat
        try:
            bat_process = subprocess.Popen(
                ["bat", "--language=yaml", "--style=plain", "--paging=never", str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Use smart_pager to handle the output
            smart_pager(bat_process, ["less", "-R"])

            # Check if bat process failed
            bat_retcode = bat_process.wait()
            if bat_retcode == 0:
                return
        except FileNotFoundError:
            pass
        except subprocess.SubprocessError:
            pass

        # Fallback to default handler
        from l_command.handlers.default import DefaultFileHandler

        DefaultFileHandler.handle(path)

    @classmethod
    def priority(cls: type["YAMLHandler"]) -> int:
        """Return the priority of the YAML handler.

        Returns:
            30 (medium priority, lower than Markdown).
        """
        return 30  # YAML has priority lower than Markdown but higher than default
