"""
Tests for MediaHandler.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from l_command.handlers.media import MediaHandler


def test_can_handle_media_extensions() -> None:
    """Test media handler detection by extension."""
    audio_extensions = [".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma"]
    video_extensions = [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp"]

    for ext in audio_extensions + video_extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, mode="wb") as tmp:
            tmp.write(b"dummy media content")  # Write some content
            tmp.flush()
            path = Path(tmp.name)
            assert MediaHandler.can_handle(path) is True, f"Failed for extension {ext}"

    # Non-media extension
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert MediaHandler.can_handle(path) is False


def test_priority() -> None:
    """Test media handler priority."""
    assert MediaHandler.priority() == 55


@patch("subprocess.run")
def test_ffprobe_timeout_handling(mock_run) -> None:
    """Test that ffprobe timeout is handled gracefully."""
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffprobe", timeout=60)

    with tempfile.NamedTemporaryFile(suffix=".mp4", mode="wb") as tmp:
        tmp.write(b"fake video content")
        tmp.flush()
        path = Path(tmp.name)

        # Should not raise an exception
        MediaHandler.handle(path)

        # Verify subprocess.run was called with timeout parameter
        assert mock_run.called
        call_args = mock_run.call_args
        assert call_args is not None
        assert "timeout" in call_args.kwargs or (len(call_args.args) > 0 and "timeout" in str(call_args))
