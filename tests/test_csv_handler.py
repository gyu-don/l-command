"""
Tests for CSVHandler.
"""

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from l_command.handlers.csv import CSVHandler

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from pytest_mock import MockerFixture


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


def test_handle_empty_csv(tmp_path: Path, capsys: "CaptureFixture") -> None:
    """Test handling empty CSV file."""
    csv_file = tmp_path / "empty.csv"
    csv_file.touch()

    CSVHandler.handle(csv_file)

    captured = capsys.readouterr()
    assert "(Empty CSV/TSV file)" in captured.out


def test_handle_csv_size_exceeds_limit(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling CSV file that exceeds size limit."""
    from l_command.handlers.csv import MAX_CSV_SIZE_BYTES

    csv_file = tmp_path / "large.csv"
    csv_file.write_text("col1,col2\nval1,val2\n")

    # Mock stat to return size over limit
    mock_stat = mocker.patch("pathlib.Path.stat")
    mock_stat_result = mocker.Mock()
    mock_stat_result.st_size = MAX_CSV_SIZE_BYTES + 1
    mock_stat.return_value = mock_stat_result

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    CSVHandler.handle(csv_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(csv_file)


def test_handle_valid_csv(tmp_path: Path, capsys: "CaptureFixture") -> None:
    """Test handling valid CSV file."""
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("name,age,city\nAlice,30,Tokyo\nBob,25,Osaka\n")

    CSVHandler.handle(csv_file)

    captured = capsys.readouterr()
    assert "CSV File:" in captured.out
    assert "Size:" in captured.out
    assert "Columns: 3" in captured.out
    assert "Total rows:" in captured.out
    assert "Alice" in captured.out
    assert "Bob" in captured.out


def test_handle_valid_tsv(tmp_path: Path, capsys: "CaptureFixture") -> None:
    """Test handling valid TSV file."""
    tsv_file = tmp_path / "test.tsv"
    tsv_file.write_text("name\tage\tcity\nCarol\t28\tKyoto\nDave\t35\tNagoya\n")

    CSVHandler.handle(tsv_file)

    captured = capsys.readouterr()
    assert "TSV File:" in captured.out
    assert "Carol" in captured.out
    assert "Dave" in captured.out


def test_handle_csv_with_semicolon_delimiter(tmp_path: Path, capsys: "CaptureFixture") -> None:
    """Test handling CSV with semicolon delimiter."""
    csv_file = tmp_path / "semicolon.csv"
    csv_file.write_text("name;age;city\nEve;32;Fukuoka\nFrank;29;Sendai\n")

    CSVHandler.handle(csv_file)

    captured = capsys.readouterr()
    assert "semicolon-separated File:" in captured.out
    assert "Eve" in captured.out


def test_handle_csv_delimiter_detection_failure(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test CSV handler when delimiter detection fails."""
    csv_file = tmp_path / "no_delimiter.csv"
    csv_file.write_text("just some text\nwithout delimiters\n")

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    CSVHandler.handle(csv_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(csv_file)


def test_handle_csv_read_error(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test CSV handler with read error."""
    csv_file = tmp_path / "error.csv"
    csv_file.write_text("col1,col2\nval1,val2\n")

    # Mock stat to succeed but file open to fail
    def mock_path_open(*args, **kwargs):
        raise OSError("Permission denied")

    mocker.patch.object(Path, "open", side_effect=mock_path_open)

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    CSVHandler.handle(csv_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(csv_file)


def test_handle_csv_with_many_rows(tmp_path: Path, capsys: "CaptureFixture") -> None:
    """Test handling CSV with many rows (shows preview)."""
    from l_command.handlers.csv import MAX_PREVIEW_ROWS

    csv_file = tmp_path / "many_rows.csv"
    with csv_file.open("w") as f:
        f.write("id,value\n")
        for i in range(MAX_PREVIEW_ROWS + 20):
            f.write(f"{i},{i*10}\n")

    CSVHandler.handle(csv_file)

    captured = capsys.readouterr()
    assert f"showing first {MAX_PREVIEW_ROWS}" in captured.out
    assert "more rows" in captured.out
