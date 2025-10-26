"""
Handler for processing image files.
"""

import logging
import subprocess
from pathlib import Path

from l_command.constants import TIMEOUT_QUICK, TIMEOUT_RENDERING
from l_command.handlers.base import FileHandler

# Constants specific to image handling
MAX_IMAGE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB limit for image processing
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

logger = logging.getLogger(__name__)


class ImageHandler(FileHandler):
    """Handler for processing image files."""

    @classmethod
    def can_handle(cls: type["ImageHandler"], path: Path) -> bool:
        """Check if the path is an image file.

        Args:
            path: The path to check.

        Returns:
            True if the path is an image file, False otherwise.
        """
        if not path.is_file():
            return False

        # Check by extension
        if path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS:
            try:
                if path.stat().st_size == 0:
                    return False
            except OSError:
                return False  # Cannot stat, likely doesn't exist or permission error
            return True

        # Check by content (common image magic bytes)
        try:
            with path.open("rb") as f:
                header = f.read(16)
                # PNG magic bytes
                if header.startswith(b"\x89PNG\r\n\x1a\n"):
                    return True
                # JPEG magic bytes
                if header.startswith(b"\xff\xd8\xff"):
                    return True
                # GIF magic bytes
                if header.startswith((b"GIF87a", b"GIF89a")):
                    return True
                # BMP magic bytes
                if header.startswith(b"BM"):
                    return True
                # WebP magic bytes
                if header.startswith(b"RIFF") and b"WEBP" in header:
                    return True
                # TIFF magic bytes
                if header.startswith((b"II*\x00", b"MM\x00*")):
                    return True
        except OSError:
            pass

        return False

    @classmethod
    def handle(cls: type["ImageHandler"], path: Path) -> None:
        """Display image file using timg with fallbacks.

        Args:
            path: The image file path to display.
        """
        try:
            file_size = path.stat().st_size
            if file_size == 0:
                print("(Empty image file)")
                return

            if file_size > MAX_IMAGE_SIZE_BYTES:
                logger.warning(
                    f"Image file size ({file_size} bytes) exceeds limit "
                    f"({MAX_IMAGE_SIZE_BYTES} bytes). "
                    f"Showing file info only.",
                )
                cls._show_image_info(path, file_size)
                return

            # Try to use timg first
            try:
                subprocess.run(
                    ["timg", "--fit-width", "--rotate=exif", str(path)],
                    check=True,
                    timeout=TIMEOUT_RENDERING,
                )
                # Show basic info after image
                print(f"\nImage: {path.name} ({file_size:,} bytes)")
                return

            except subprocess.TimeoutExpired:
                logger.warning(
                    f"timg timed out after {TIMEOUT_RENDERING}s while rendering {path.name}.",
                )
                cls._show_image_info(path, file_size)
                return

            except FileNotFoundError:
                logger.warning(
                    "timg command not found. Install with your package manager.",
                )
                cls._show_image_info(path, file_size)
                return

            except subprocess.CalledProcessError as e:
                logger.warning(f"timg failed to display image: {e}")
                cls._show_image_info(path, file_size)
                return

        except OSError as e:
            logger.error(
                f"Error accessing image file: {e}",
            )
            # Fallback if we can't even get the file size
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def _show_image_info(cls: type["ImageHandler"], path: Path, file_size: int) -> None:
        """Show basic image information.

        Args:
            path: The image file path.
            file_size: The file size in bytes.
        """
        print(f"Image File: {path.name}")
        print(f"Type: {path.suffix.upper().lstrip('.')} image")
        print(f"Size: {file_size:,} bytes")

        # Try to get image dimensions using file command
        try:
            result = subprocess.run(
                ["file", str(path)],
                capture_output=True,
                text=True,
                check=True,
                timeout=TIMEOUT_QUICK,
            )
            output = result.stdout.strip()
            # Extract dimensions if available in file output
            if "," in output and ("x" in output or "×" in output):
                # Look for dimension patterns like "1920 x 1080" or "1920x1080"
                import re

                dimension_match = re.search(r"(\d+)\s*[x×]\s*(\d+)", output)
                if dimension_match:
                    width, height = dimension_match.groups()
                    print(f"Dimensions: {width} × {height} pixels")
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass

        print("(Install 'timg' for terminal image display)")

    @classmethod
    def priority(cls: type["ImageHandler"]) -> int:
        """Return the priority of the Image handler.

        Returns:
            65 (high priority, higher than PDF).
        """
        return 65  # Image has higher priority than PDF
