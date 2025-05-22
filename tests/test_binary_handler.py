"""
Tests for the binary handler module.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from l_command.handlers.binary import BinaryHandler


def create_binary_file(path: Path, content: bytes) -> None:
    """Create a binary file with the given content."""
    path.write_bytes(content)


def create_text_file(path: Path, content: str) -> None:
    """Create a text file with the given content."""
    with path.open("w", encoding="utf-8") as f:
        f.write(content)


def test_can_handle_binary_and_text(tmp_path: Path) -> None:
    """Test that BinaryHandler can handle binary files but not text files."""
    # Binary file
    binary_file = tmp_path / "test.bin"
    create_binary_file(binary_file, b"\x00\x01\x02\x03")
    assert BinaryHandler.can_handle(binary_file) is True

    # Text file
    text_file = tmp_path / "test.txt"
    create_text_file(text_file, "This is a text file.")
    assert BinaryHandler.can_handle(text_file) is False

    # Empty file
    empty_file = tmp_path / "empty.bin"
    create_binary_file(empty_file, b"")
    assert BinaryHandler.can_handle(empty_file) is False


def test_can_handle_with_file_command(tmp_path: Path) -> None:
    """Test BinaryHandler.can_handle with the file command."""
    # Create a binary file
    binary_file = tmp_path / "filecmd.bin"
    create_binary_file(binary_file, b"\x00\x01\x02")
    
    # Mock the file command to return "binary"
    with patch("shutil.which", lambda cmd: True if cmd == "file" else None), \
         patch("subprocess.run", return_value=MagicMock(stdout="binary\n", returncode=0)):
        assert BinaryHandler.can_handle(binary_file) is True

    # Mock the file command to return "us-ascii" but content is binary
    with patch("shutil.which", lambda cmd: True if cmd == "file" else None), \
         patch("subprocess.run", return_value=MagicMock(stdout="us-ascii\n", returncode=0)):
        assert BinaryHandler.can_handle(binary_file) is True  # fallback to content check


def test_handle_binary_file_with_hexdump(tmp_path: Path) -> None:
    """Test handling a binary file with hexdump."""
    # Create a binary file
    binary_file = tmp_path / "test.bin"
    create_binary_file(binary_file, b"\x00\x01\x02\x03")
    
    # Mock the which function to return the path to hexdump
    with patch("shutil.which", return_value="/usr/bin/hexdump"):
        # Mock the Popen process
        mock_hexdump_process = MagicMock()
        mock_hexdump_process.stdout = MagicMock()
        mock_hexdump_process.wait.return_value = 0
        
        with patch("subprocess.Popen", return_value=mock_hexdump_process) as mock_popen, \
             patch("l_command.handlers.binary.smart_pager") as mock_pager:
            BinaryHandler.handle(binary_file)
            
            # Verify Popen was called with hexdump command
            mock_popen.assert_called_with(
                ["hexdump", "-C", str(binary_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            
            # Verify smart_pager was called with the process
            mock_pager.assert_called_once_with(mock_hexdump_process, ["less", "-R"])


def test_handle_hexdump_not_found(tmp_path: Path) -> None:
    """Test handling a binary file when hexdump is not available."""
    # Create a binary file
    binary_file = tmp_path / "nohexdump.bin"
    create_binary_file(binary_file, b"\x00\x01\x02\x03")
    
    # Mock the which function to return None for hexdump
    with patch("shutil.which", return_value=None), \
         patch("l_command.handlers.binary.logger") as mock_logger:
        BinaryHandler.handle(binary_file)
        
        # Verify error was logged
        mock_logger.error.assert_called_once_with(
            "Error: 'hexdump' command not found. Cannot display binary file."
        )
