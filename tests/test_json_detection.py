import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from l_command.handlers.json import JsonHandler


def test_should_try_jq_by_extension() -> None:
    """Test JSON handler detection by extension."""
    # File with .json extension (non-empty)
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w") as tmp:
        tmp.write("{}")  # Write minimal content to make it non-empty
        tmp.flush()
        path = Path(tmp.name)
        assert JsonHandler.can_handle(path) is True

    # File with .JSON extension (uppercase, non-empty)
    with tempfile.NamedTemporaryFile(suffix=".JSON", mode="w") as tmp:
        tmp.write("[]")  # Write minimal content
        tmp.flush()
        path = Path(tmp.name)
        assert JsonHandler.can_handle(path) is True

    # Empty file with .json extension
    with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
        path = Path(tmp.name)
        assert JsonHandler.can_handle(path) is False  # Empty .json should return False

    # File with non-JSON extension
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert JsonHandler.can_handle(path) is False


def test_should_try_jq_by_content() -> None:
    """Test JSON handler detection by content for non-json extensions."""
    # JSON object content
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        tmp.write(b' { "key": "value" } ')  # Add spaces to test strip()
        tmp.flush()
        path = Path(tmp.name)
        assert JsonHandler.can_handle(path) is True

    # JSON array content
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        tmp.write(b" [1, 2, 3] ")
        tmp.flush()
        path = Path(tmp.name)
        assert JsonHandler.can_handle(path) is True

    # Non-JSON content starting with { or [
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        tmp.write(b"{not really json")
        tmp.flush()
        path = Path(tmp.name)
        assert JsonHandler.can_handle(path) is True  # Still matches based on start char

    # Non-JSON content
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        tmp.write(b"This is not JSON")
        tmp.flush()
        path = Path(tmp.name)
        assert JsonHandler.can_handle(path) is False

    # Empty file
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert JsonHandler.can_handle(path) is False


def test_should_try_jq_with_test_files() -> None:
    """Test with prepared test files."""
    test_files_dir = Path(__file__).parent / "test_files"

    # Valid JSON file (assume non-empty)
    valid_json = test_files_dir / "valid.json"
    assert JsonHandler.can_handle(valid_json) is True

    # Invalid JSON file (has .json extension, assume non-empty)
    invalid_json = test_files_dir / "invalid.json"
    # JsonHandler.can_handle returns True based on extension and non-zero size.
    # The actual validation happens later.
    assert JsonHandler.can_handle(invalid_json) is True

    # Non-JSON file
    not_json = test_files_dir / "not_json.txt"
    assert JsonHandler.can_handle(not_json) is False

    # Empty file with json extension
    empty_json = test_files_dir / "empty.json"  # Assuming this exists
    if empty_json.exists():  # Add check in case it doesn't
        assert JsonHandler.can_handle(empty_json) is False


@patch("subprocess.run")
def test_jq_timeout_handling(mock_run: MagicMock) -> None:
    """Test that jq timeout is handled gracefully."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="jq", timeout=30)

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w") as tmp:
        tmp.write('{"key": "value"}')
        tmp.flush()
        path = Path(tmp.name)

        # Should not raise an exception
        JsonHandler.handle(path)

        # Verify subprocess.run was called with timeout parameter
        assert mock_run.called
        call_args = mock_run.call_args
        assert call_args is not None
        assert "timeout" in call_args.kwargs or (len(call_args.args) > 0 and "timeout" in str(call_args))
