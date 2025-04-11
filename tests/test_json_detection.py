import tempfile
from pathlib import Path

from l_command.cli import is_json_file


def test_is_json_file_by_extension() -> None:
    """Test JSON file detection by extension."""
    # File with .json extension
    with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
        path = Path(tmp.name)
        assert is_json_file(path) is True

    # File with .JSON extension (uppercase)
    with tempfile.NamedTemporaryFile(suffix=".JSON") as tmp:
        path = Path(tmp.name)
        assert is_json_file(path) is True

    # File with non-JSON extension
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert is_json_file(path) is False


def test_is_json_file_by_content() -> None:
    """Test JSON file detection by content."""
    # JSON object content
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        tmp.write(b'{"key": "value"}')
        tmp.flush()
        path = Path(tmp.name)
        assert is_json_file(path) is True

    # JSON array content
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        tmp.write(b"[1, 2, 3]")
        tmp.flush()
        path = Path(tmp.name)
        assert is_json_file(path) is True

    # Non-JSON content
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        tmp.write(b"This is not JSON")
        tmp.flush()
        path = Path(tmp.name)
        assert is_json_file(path) is False

    # Empty file
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert is_json_file(path) is False


def test_is_json_file_with_test_files() -> None:
    """Test with prepared test files."""
    test_files_dir = Path(__file__).parent / "test_files"

    # Valid JSON file
    valid_json = test_files_dir / "valid.json"
    assert is_json_file(valid_json) is True

    # Invalid JSON file (has JSON-like format but invalid)
    invalid_json = test_files_dir / "invalid.json"
    assert is_json_file(invalid_json) is False

    # Non-JSON file
    not_json = test_files_dir / "not_json.txt"
    assert is_json_file(not_json) is False
