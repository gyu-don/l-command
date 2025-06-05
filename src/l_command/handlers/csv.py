"""
Handler for processing CSV and TSV files.
"""

import csv
import logging
from pathlib import Path

from l_command.handlers.base import FileHandler

# Constants specific to CSV/TSV handling
MAX_CSV_SIZE_BYTES = 100 * 1024 * 1024  # 100MB limit for CSV processing
MAX_PREVIEW_ROWS = 50  # Maximum number of rows to preview
MAX_COLUMN_WIDTH = 30  # Maximum width for each column in preview
SUPPORTED_CSV_EXTENSIONS = {".csv", ".tsv", ".txt"}

logger = logging.getLogger(__name__)


class CSVHandler(FileHandler):
    """Handler for processing CSV and TSV files."""

    @classmethod
    def can_handle(cls: type["CSVHandler"], path: Path) -> bool:
        """Check if the path is a CSV or TSV file.

        Args:
            path: The path to check.

        Returns:
            True if the path is a CSV/TSV file, False otherwise.
        """
        if not path.is_file():
            return False

        # Check by extension
        if path.suffix.lower() in SUPPORTED_CSV_EXTENSIONS:
            try:
                if path.stat().st_size == 0:
                    return False
                # For .txt files, we need content-based detection
                if path.suffix.lower() == ".txt":
                    return cls._detect_csv_content(path)
                return True
            except OSError:
                return False  # Cannot stat, likely doesn't exist or permission error

        return False

    @classmethod
    def _detect_csv_content(cls: type["CSVHandler"], path: Path) -> bool:
        """Detect if a file contains CSV/TSV content.

        Args:
            path: The file path to check.

        Returns:
            True if the file appears to contain CSV/TSV data, False otherwise.
        """
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                # Read first few lines to detect CSV/TSV pattern
                lines = []
                for i, line in enumerate(f):
                    lines.append(line.strip())
                    if i >= 5:  # Check first 5 lines
                        break

                if len(lines) < 2:
                    return False

                # Check for consistent delimiters
                for delimiter in [",", "\t", ";", "|"]:
                    delimiter_counts = [line.count(delimiter) for line in lines if line]
                    if delimiter_counts and all(
                        count > 0 and count == delimiter_counts[0] for count in delimiter_counts
                    ):
                        return True
        except (OSError, UnicodeError):
            pass

        return False

    @classmethod
    def handle(cls: type["CSVHandler"], path: Path) -> None:
        """Display CSV/TSV file with column structure visualization.

        Args:
            path: The CSV/TSV file path to display.
        """
        try:
            file_size = path.stat().st_size
            if file_size == 0:
                print("(Empty CSV/TSV file)")
                return

            if file_size > MAX_CSV_SIZE_BYTES:
                logger.warning(
                    f"CSV/TSV file size ({file_size} bytes) exceeds limit "
                    f"({MAX_CSV_SIZE_BYTES} bytes). "
                    f"Falling back to default viewer.",
                )
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            # Detect delimiter and process CSV
            delimiter = cls._detect_delimiter(path)
            if delimiter is None:
                logger.warning("Could not detect CSV delimiter. Falling back to default viewer.")
                from l_command.handlers.default import DefaultFileHandler

                DefaultFileHandler.handle(path)
                return

            cls._display_csv_content(path, delimiter, file_size)

        except OSError as e:
            logger.error(
                f"Error accessing CSV/TSV file: {e}",
            )
            # Fallback if we can't even get the file size
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def _detect_delimiter(cls: type["CSVHandler"], path: Path) -> str | None:
        """Detect the delimiter used in the CSV file.

        Args:
            path: The CSV file path.

        Returns:
            The detected delimiter or None if detection failed.
        """
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                # Read a sample of the file
                sample = f.read(8192)

                # Use csv.Sniffer to detect delimiter
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample, delimiters=",\t;|")
                    return dialect.delimiter
                except csv.Error:
                    # Fallback: manually check common delimiters
                    for delimiter in [",", "\t", ";", "|"]:
                        lines = sample.split("\n")[:5]  # Check first 5 lines
                        if lines:
                            delimiter_counts = [line.count(delimiter) for line in lines if line.strip()]
                            if delimiter_counts and all(
                                count > 0 and count == delimiter_counts[0] for count in delimiter_counts
                            ):
                                return delimiter
        except (OSError, UnicodeError):
            pass

        return None

    @classmethod
    def _display_csv_content(cls: type["CSVHandler"], path: Path, delimiter: str, file_size: int) -> None:
        """Display CSV content with formatted table structure.

        Args:
            path: The CSV file path.
            delimiter: The CSV delimiter.
            file_size: The file size in bytes.
        """
        delimiter_name = {",": "CSV", "\t": "TSV", ";": "semicolon-separated", "|": "pipe-separated"}.get(
            delimiter, "delimited"
        )
        print(f"{delimiter_name} File: {path.name}")
        print(f"Size: {file_size:,} bytes")

        try:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f, delimiter=delimiter)

                rows = []
                total_rows = 0
                headers = None

                for i, row in enumerate(reader):
                    total_rows += 1
                    if i == 0:
                        headers = row
                        rows.append(row)
                    elif i < MAX_PREVIEW_ROWS:
                        rows.append(row)
                    elif i == MAX_PREVIEW_ROWS:
                        break

                if not rows:
                    print("(No data found)")
                    return

                print(f"Columns: {len(headers) if headers else 'Unknown'}")
                showing_text = f" (showing first {MAX_PREVIEW_ROWS})" if total_rows > MAX_PREVIEW_ROWS else ""
                print(f"Total rows: {total_rows:,}{showing_text}")
                print("-" * 50)

                # Display table structure
                if headers:
                    # Calculate column widths
                    col_widths = []
                    for col_idx in range(len(headers)):
                        max_width = len(str(headers[col_idx]))
                        for row in rows[1:]:  # Skip header row
                            if col_idx < len(row):
                                max_width = max(max_width, len(str(row[col_idx])))
                        col_widths.append(min(max_width, MAX_COLUMN_WIDTH))

                    # Display header
                    header_row = ""
                    for i, (header, width) in enumerate(zip(headers, col_widths, strict=False)):
                        header_text = str(header)[:width]
                        header_row += f"{header_text:<{width}}"
                        if i < len(headers) - 1:
                            header_row += " | "
                    print(header_row)

                    # Display separator
                    separator = ""
                    for i, width in enumerate(col_widths):
                        separator += "-" * width
                        if i < len(col_widths) - 1:
                            separator += "-+-"
                    print(separator)

                    # Display data rows
                    for row in rows[1:]:
                        data_row = ""
                        for i, width in enumerate(col_widths):
                            cell_text = str(row[i])[:width] if i < len(row) else ""
                            data_row += f"{cell_text:<{width}}"
                            if i < len(col_widths) - 1:
                                data_row += " | "
                        print(data_row)

                if total_rows > MAX_PREVIEW_ROWS:
                    print(f"\n... and {total_rows - MAX_PREVIEW_ROWS} more rows")
                    print("(Use default text viewer to see full content)")

        except Exception as e:
            logger.warning(f"Error reading CSV content: {e}")
            print("(Error reading CSV content. Falling back to default viewer.)")
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def priority(cls: type["CSVHandler"]) -> int:
        """Return the priority of the CSV handler.

        Returns:
            40 (medium priority, lower than XML).
        """
        return 40  # CSV has priority lower than XML but higher than default
