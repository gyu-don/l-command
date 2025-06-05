"""
Tests for CSVHandler.
"""

import tempfile
from pathlib import Path

from l_command.handlers.csv import CSVHandler


def test_can_handle_csv_extensions() -> None:
    """Test CSV handler detection by extension."""
    # CSV file
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w") as tmp:
        tmp.write("name,age,city\nJohn,30,NYC")
        tmp.flush()
        path = Path(tmp.name)
        assert CSVHandler.can_handle(path) is True

    # TSV file
    with tempfile.NamedTemporaryFile(suffix=".tsv", mode="w") as tmp:
        tmp.write("name\tage\tcity\nJohn\t30\tNYC")
        tmp.flush()
        path = Path(tmp.name)
        assert CSVHandler.can_handle(path) is True

    # Text file with CSV content
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("col1,col2,col3\nval1,val2,val3\nval4,val5,val6")
        tmp.flush()
        path = Path(tmp.name)
        assert CSVHandler.can_handle(path) is True

    # Text file without CSV content
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("This is just regular text without delimiters")
        tmp.flush()
        path = Path(tmp.name)
        assert CSVHandler.can_handle(path) is False


def test_priority() -> None:
    """Test CSV handler priority."""
    assert CSVHandler.priority() == 40
