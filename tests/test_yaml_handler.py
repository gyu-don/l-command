"""
Tests for YAMLHandler.
"""

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from l_command.handlers.yaml import YAMLHandler

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from pytest_mock import MockerFixture


def test_can_handle_yaml_extensions() -> None:
    """Test YAML handler detection by extension."""
    extensions = [".yaml", ".yml"]

    for ext in extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, mode="w") as tmp:
            tmp.write("key: value\nlist:\n  - item1\n  - item2")
            tmp.flush()
            path = Path(tmp.name)
            assert YAMLHandler.can_handle(path) is True, f"Failed for extension {ext}"

    # Non-YAML extension
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert YAMLHandler.can_handle(path) is False


def test_can_handle_yaml_content() -> None:
    """Test YAML handler detection by content."""
    # YAML document separator
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("---\nkey: value\nother: data")
        tmp.flush()
        path = Path(tmp.name)
        assert YAMLHandler.can_handle(path) is True

    # YAML version directive
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("%YAML 1.2\n---\nkey: value")
        tmp.flush()
        path = Path(tmp.name)
        assert YAMLHandler.can_handle(path) is True

    # YAML-like structure
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("key1: value1\nkey2: value2\nlist:\n  - item1\n  - item2")
        tmp.flush()
        path = Path(tmp.name)
        assert YAMLHandler.can_handle(path) is True

    # Non-YAML content
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w") as tmp:
        tmp.write("This is just regular text")
        tmp.flush()
        path = Path(tmp.name)
        assert YAMLHandler.can_handle(path) is False


def test_priority() -> None:
    """Test YAML handler priority."""
    assert YAMLHandler.priority() == 30


def test_handle_empty_yaml(tmp_path: Path, capsys: "CaptureFixture") -> None:
    """Test handling empty YAML file."""
    yaml_file = tmp_path / "empty.yaml"
    yaml_file.touch()

    YAMLHandler.handle(yaml_file)

    captured = capsys.readouterr()
    assert "(Empty YAML file)" in captured.out


def test_handle_yaml_size_exceeds_limit(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling YAML file that exceeds size limit."""
    from l_command.handlers.yaml import MAX_YAML_SIZE_BYTES

    yaml_file = tmp_path / "large.yaml"
    yaml_file.write_text("key: value")

    # Mock stat to return size over limit
    mock_stat = mocker.patch("pathlib.Path.stat")
    mock_stat_result = mocker.Mock()
    mock_stat_result.st_size = MAX_YAML_SIZE_BYTES + 1
    mock_stat.return_value = mock_stat_result

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    YAMLHandler.handle(yaml_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(yaml_file)


def test_handle_yaml_with_yq_format(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling YAML with yq formatter."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("key: value\nlist:\n  - item1\n  - item2")

    # Mock yq available
    mock_popen = mocker.patch("subprocess.Popen")
    mock_process = mocker.Mock()
    mock_process.stdout = mocker.Mock()
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    # Mock smart_pager
    mock_pager = mocker.patch("l_command.handlers.yaml.smart_pager")

    YAMLHandler.handle(yaml_file)

    # Verify yq was called
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert "yq" in args[0]
    assert "--colors" in args


def test_handle_yaml_with_yq_validate(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling YAML with yq validation (format failed)."""
    yaml_file = tmp_path / "test.yml"
    yaml_file.write_text("key: value")

    # Mock smart_pager to avoid the read issue
    mock_pager = mocker.patch("l_command.handlers.yaml.smart_pager")

    # Mock yq format failing
    mock_popen = mocker.patch("subprocess.Popen")
    mock_process = mocker.Mock()
    mock_process.stdout = mocker.Mock()
    mock_process.wait.return_value = 1  # Format failed
    mock_popen.return_value = mock_process

    # Mock yq validate succeeding
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.returncode = 0
    mock_result.stdout = "1"
    mock_run.return_value = mock_result

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    YAMLHandler.handle(yaml_file)

    # Should show validation info and content
    captured = capsys.readouterr()
    assert "YAML File:" in captured.out or mock_default.called


def test_handle_yaml_no_yq(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling YAML when yq is not available."""
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text("key: value")

    # Mock yq not available
    mocker.patch("subprocess.Popen", side_effect=FileNotFoundError("yq not found"))
    mocker.patch("subprocess.run", side_effect=FileNotFoundError("yq not found"))

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    YAMLHandler.handle(yaml_file)

    # Should show source with info
    captured = capsys.readouterr()
    assert "YAML File:" in captured.out or mock_default.called


def test_handle_yaml_os_error(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling YAML with OS error."""
    yaml_file = tmp_path / "error.yaml"
    yaml_file.write_text("key: value")

    # Mock stat to raise OSError
    mocker.patch.object(Path, "stat", side_effect=OSError("Permission denied"))

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    YAMLHandler.handle(yaml_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(yaml_file)
