"""
Tests for MediaHandler.
"""

import tempfile
from pathlib import Path

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
