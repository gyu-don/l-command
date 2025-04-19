# Implementation Examples

This document provides examples of extending the `l` command with new handlers.

## YAML File Handler Implementation Example

Below is an example of a handler for YAML files using the current handler-based architecture:

```python
"""
Handler for processing YAML files.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from l_command.constants import YAML_CONTENT_CHECK_BYTES, MAX_YAML_SIZE_BYTES
from l_command.handlers.base import FileHandler
from l_command.utils import count_lines


class YamlHandler(FileHandler):
    """Handler for YAML files."""

    @classmethod
    def can_handle(cls, path: Path) -> bool:
        """Check if the path is a YAML file.

        Args:
            path: The path to check.

        Returns:
            True if the path is a YAML file, False otherwise.
        """
        if not path.is_file():
            return False

        # Check by extension
        if path.suffix.lower() in [".yaml", ".yml"]:
            try:
                if path.stat().st_size == 0:
                    return False
            except OSError:
                return False  # Cannot stat, likely doesn't exist or permission error
            return True

        # Check by content
        try:
            with path.open("rb") as f:
                content_start = f.read(YAML_CONTENT_CHECK_BYTES)
                if not content_start:
                    return False
                try:
                    content_text = content_start.decode("utf-8").strip()
                    # Detect YAML-specific patterns
                    if ":" in content_text and not content_text.startswith(("{", "[")):
                        return True
                except UnicodeDecodeError:
                    pass
        except OSError:
            pass

        return False

    @classmethod
    def handle(cls, path: Path) -> None:
        """Display YAML file using yq with fallbacks.

        Args:
            path: The YAML file path to display.
        """
        try:
            file_size = path.stat().st_size
            if file_size == 0:
                print("(Empty file)")
                return

            if file_size > MAX_YAML_SIZE_BYTES:
                print(
                    f"File size ({file_size} bytes) exceeds limit "
                    f"({MAX_YAML_SIZE_BYTES} bytes). "
                    f"Falling back to default viewer.",
                    file=sys.stderr,
                )
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Check if yq is available
            if not shutil.which("yq"):
                print("yq command not found. Falling back to default viewer.", file=sys.stderr)
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Count lines to determine whether to use less
            line_count = count_lines(path)

            # Get terminal height
            try:
                terminal_height = os.get_terminal_size().lines
            except OSError:
                terminal_height = float("inf")  # Always use direct output

            # Display YAML with yq
            try:
                if line_count > terminal_height:
                    # For YAML files taller than terminal, use less with color
                    yq_process = subprocess.Popen(
                        ["yq", ".", str(path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    subprocess.run(
                        ["less", "-R"],  # -R preserves color codes
                        stdin=yq_process.stdout,
                        check=True,
                    )
                    yq_process.stdout.close()
                    # Check if yq process failed
                    yq_retcode = yq_process.wait()
                    if yq_retcode != 0:
                        print(f"yq process exited with code {yq_retcode}", file=sys.stderr)
                        from l_command.handlers.default import DefaultFileHandler

                        DefaultFileHandler.handle(path)
                else:
                    # For small YAML files, display directly
                    subprocess.run(["yq", ".", str(path)], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error displaying YAML with yq: {e}", file=sys.stderr)
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
            except OSError as e:
                print(f"Error running yq command: {e}", file=sys.stderr)
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)

        except OSError as e:
            print(f"Error accessing file stats for YAML processing: {e}", file=sys.stderr)
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def priority(cls) -> int:
        """Return the priority of the YAML handler.

        Returns:
            70 (medium-high priority, between JSON and Archive).
        """
        return 70  # YAML has higher priority than JSON but lower than Archive
```

## CSV File Handler Implementation Example

Below is an example of a handler for CSV files:

```python
"""
Handler for processing CSV and TSV files.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from l_command.handlers.base import FileHandler
from l_command.utils import count_lines


class CsvHandler(FileHandler):
    """Handler for CSV and TSV files."""

    @classmethod
    def can_handle(cls, path: Path) -> bool:
        """Check if the path is a CSV or TSV file.

        Args:
            path: The path to check.

        Returns:
            True if the path is a CSV or TSV file, False otherwise.
        """
        if not path.is_file():
            return False

        # Check by extension
        if path.suffix.lower() in [".csv", ".tsv"]:
            try:
                if path.stat().st_size == 0:
                    return False
            except OSError:
                return False
            return True

        # Check by content
        try:
            with path.open("rb") as f:
                content_start = f.read(1024)
                if not content_start:
                    return False
                try:
                    content_text = content_start.decode("utf-8")
                    # Detect lines with many commas
                    lines = content_text.split("\n")
                    if len(lines) >= 2:
                        commas_in_first_line = lines[0].count(",")
                        if commas_in_first_line >= 2:
                            # Check if second line has similar comma count
                            if len(lines) > 1 and abs(lines[1].count(",") - commas_in_first_line) <= 1:
                                return True
                except UnicodeDecodeError:
                    pass
        except OSError:
            pass

        return False

    @classmethod
    def handle(cls, path: Path) -> None:
        """Display CSV file using column command for better formatting.

        Args:
            path: The CSV file path to display.
        """
        delimiter = "," if path.suffix.lower() == ".csv" else "\t"

        try:
            file_size = path.stat().st_size
            if file_size == 0:
                print("(Empty file)")
                return

            # Size limit for CSV processing
            if file_size > 5 * 1024 * 1024:  # 5MB
                print(
                    f"File size ({file_size} bytes) exceeds limit. "
                    f"Falling back to default viewer.",
                    file=sys.stderr,
                )
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Check if column command is available
            if not shutil.which("column"):
                print("column command not found. Falling back to default viewer.", file=sys.stderr)
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Get terminal height
            try:
                terminal_height = os.get_terminal_size().lines
            except OSError:
                terminal_height = float("inf")  # Always use direct output

            line_count = count_lines(path)

            try:
                if line_count > terminal_height:
                    # For CSV files taller than terminal, use less with horizontal scroll
                    column_process = subprocess.Popen(
                        ["column", "-t", "-s", delimiter, str(path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    subprocess.run(
                        ["less", "-S"],  # -S enables horizontal scrolling
                        stdin=column_process.stdout,
                        check=True,
                    )
                    column_process.stdout.close()
                    column_retcode = column_process.wait()
                    if column_retcode != 0:
                        print(f"column process exited with code {column_retcode}", file=sys.stderr)
                        from l_command.handlers.default import DefaultFileHandler

                        DefaultFileHandler.handle(path)
                else:
                    # For small CSV files, display directly
                    subprocess.run(["column", "-t", "-s", delimiter, str(path)], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error displaying CSV with column: {e}", file=sys.stderr)
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
            except OSError as e:
                print(f"Error running column command: {e}", file=sys.stderr)
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)

        except OSError as e:
            print(f"Error accessing file stats for CSV processing: {e}", file=sys.stderr)
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def priority(cls) -> int:
        """Return the priority of the CSV handler.

        Returns:
            40 (medium priority, lower than JSON).
        """
        return 40  # CSV has lower priority than JSON
```

## Implementation Checklist

When adding a new file type handler, follow this checklist:

1. **Add Constants**:
   - Add necessary constants to `constants.py` (size limits, etc.)

2. **Create Handler Class**:
   - Create a new class that inherits from `FileHandler`
   - Implement `can_handle()` method:
     - Extension-based detection
     - Content-based detection (optional)
     - Error handling
   - Implement `handle()` method:
     - Size checks
     - External command existence checks
     - Paging processing (as needed)
     - Error handling and fallbacks
   - Implement `priority()` method:
     - Choose an appropriate priority relative to existing handlers

3. **Register Handler**:
   - Add the handler to the list in `handlers/__init__.py`

4. **Create Tests**:
   - Test the detection method
   - Test the display method (using mocks)
   - Test error cases
