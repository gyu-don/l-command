"""
Tests for ImageHandler.
"""

import tempfile
from pathlib import Path

from l_command.handlers.image import ImageHandler


def test_can_handle_image_extensions() -> None:
    """Test image handler detection by extension."""
    extensions = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"]

    for ext in extensions:
        with tempfile.NamedTemporaryFile(suffix=ext, mode="wb") as tmp:
            tmp.write(b"dummy image content")  # Write some content
            tmp.flush()
            path = Path(tmp.name)
            assert ImageHandler.can_handle(path) is True, f"Failed for extension {ext}"

    # Non-image extension
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert ImageHandler.can_handle(path) is False


def test_can_handle_image_content() -> None:
    """Test image handler detection by content."""
    # PNG magic bytes
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb") as tmp:
        tmp.write(b"\x89PNG\r\n\x1a\n" + b"dummy content")
        tmp.flush()
        path = Path(tmp.name)
        assert ImageHandler.can_handle(path) is True

    # JPEG magic bytes
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb") as tmp:
        tmp.write(b"\xff\xd8\xff" + b"dummy content")
        tmp.flush()
        path = Path(tmp.name)
        assert ImageHandler.can_handle(path) is True

    # GIF magic bytes
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb") as tmp:
        tmp.write(b"GIF87a" + b"dummy content")
        tmp.flush()
        path = Path(tmp.name)
        assert ImageHandler.can_handle(path) is True

    # Non-image content
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb") as tmp:
        tmp.write(b"This is not an image")
        tmp.flush()
        path = Path(tmp.name)
        assert ImageHandler.can_handle(path) is False


def test_priority() -> None:
    """Test image handler priority."""
    assert ImageHandler.priority() == 65
