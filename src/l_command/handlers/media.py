"""
Handler for processing audio and video files.
"""

import json
import logging
import subprocess
from pathlib import Path

from l_command.handlers.base import FileHandler

# Constants specific to media handling
MAX_MEDIA_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2GB limit for media processing
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".flac", ".wav", ".aac", ".ogg", ".m4a", ".wma"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp"}
SUPPORTED_MEDIA_EXTENSIONS = SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)


class MediaHandler(FileHandler):
    """Handler for processing audio and video files."""

    @classmethod
    def can_handle(cls: type["MediaHandler"], path: Path) -> bool:
        """Check if the path is a media file.

        Args:
            path: The path to check.

        Returns:
            True if the path is a media file, False otherwise.
        """
        if not path.is_file():
            return False

        # Check by extension
        if path.suffix.lower() in SUPPORTED_MEDIA_EXTENSIONS:
            try:
                if path.stat().st_size == 0:
                    return False
            except OSError:
                return False  # Cannot stat, likely doesn't exist or permission error
            return True

        return False

    @classmethod
    def handle(cls: type["MediaHandler"], path: Path) -> None:
        """Display media file information using ffprobe.

        Args:
            path: The media file path to display.
        """
        try:
            file_size = path.stat().st_size
            if file_size == 0:
                print("(Empty media file)")
                return

            if file_size > MAX_MEDIA_SIZE_BYTES:
                logger.warning(
                    f"Media file size ({file_size} bytes) exceeds limit "
                    f"({MAX_MEDIA_SIZE_BYTES} bytes). "
                    f"Showing basic file info only.",
                )
                cls._show_basic_info(path, file_size)
                return

            # Try to use ffprobe to get media information
            try:
                result = subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "quiet",
                        "-print_format",
                        "json",
                        "-show_format",
                        "-show_streams",
                        str(path),
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )

                media_info = json.loads(result.stdout)
                cls._display_media_info(path, file_size, media_info)
                return

            except FileNotFoundError:
                logger.warning(
                    "ffprobe command not found. Install FFmpeg package.",
                )
                cls._show_basic_info(path, file_size)
                return

            except subprocess.CalledProcessError as e:
                logger.warning(f"ffprobe failed to analyze media: {e}")
                cls._show_basic_info(path, file_size)
                return

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse ffprobe output: {e}")
                cls._show_basic_info(path, file_size)
                return

        except OSError as e:
            logger.error(
                f"Error accessing media file: {e}",
            )
            # Fallback if we can't even get the file size
            from l_command.handlers.default import DefaultFileHandler

            DefaultFileHandler.handle(path)

    @classmethod
    def _display_media_info(cls: type["MediaHandler"], path: Path, file_size: int, media_info: dict) -> None:
        """Display detailed media information from ffprobe.

        Args:
            path: The media file path.
            file_size: The file size in bytes.
            media_info: The parsed ffprobe JSON output.
        """
        print(f"Media File: {path.name}")
        print(f"Size: {file_size:,} bytes")

        # Get format information
        format_info = media_info.get("format", {})
        format_name = format_info.get("format_long_name", "Unknown format")
        duration = format_info.get("duration")
        bitrate = format_info.get("bit_rate")

        print(f"Format: {format_name}")

        if duration:
            try:
                duration_sec = float(duration)
                hours = int(duration_sec // 3600)
                minutes = int((duration_sec % 3600) // 60)
                seconds = int(duration_sec % 60)
                if hours > 0:
                    print(f"Duration: {hours:02d}:{minutes:02d}:{seconds:02d}")
                else:
                    print(f"Duration: {minutes:02d}:{seconds:02d}")
            except ValueError:
                print(f"Duration: {duration}")

        if bitrate:
            try:
                bitrate_kbps = int(bitrate) // 1000
                print(f"Bitrate: {bitrate_kbps:,} kbps")
            except ValueError:
                print(f"Bitrate: {bitrate}")

        # Process streams
        streams = media_info.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        # Display video stream info
        if video_streams:
            print("\nVideo Streams:")
            for i, stream in enumerate(video_streams):
                codec_name = stream.get("codec_long_name", stream.get("codec_name", "Unknown"))
                width = stream.get("width")
                height = stream.get("height")
                fps = stream.get("r_frame_rate", "")

                stream_info = f"  Stream {i}: {codec_name}"
                if width and height:
                    stream_info += f", {width}×{height}"
                if fps and "/" in fps:
                    try:
                        num, den = fps.split("/")
                        fps_val = int(num) / int(den)
                        stream_info += f", {fps_val:.1f} fps"
                    except (ValueError, ZeroDivisionError):
                        pass
                print(stream_info)

        # Display audio stream info
        if audio_streams:
            print("\nAudio Streams:")
            for i, stream in enumerate(audio_streams):
                codec_name = stream.get("codec_long_name", stream.get("codec_name", "Unknown"))
                sample_rate = stream.get("sample_rate")
                channels = stream.get("channels")

                stream_info = f"  Stream {i}: {codec_name}"
                if channels:
                    stream_info += f", {channels} channel{'s' if int(channels) != 1 else ''}"
                if sample_rate:
                    stream_info += f", {sample_rate} Hz"
                print(stream_info)

        # Show metadata if available
        tags = format_info.get("tags", {})
        if tags:
            print("\nMetadata:")
            for key, value in tags.items():
                # Common tags to display
                if key.lower() in ["title", "artist", "album", "date", "genre", "track"]:
                    print(f"  {key.title()}: {value}")

    @classmethod
    def _show_basic_info(cls: type["MediaHandler"], path: Path, file_size: int) -> None:
        """Show basic media file information.

        Args:
            path: The media file path.
            file_size: The file size in bytes.
        """
        print(f"Media File: {path.name}")

        # Determine if it's audio or video based on extension
        if path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS:
            print("Type: Audio file")
        elif path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
            print("Type: Video file")
        else:
            print("Type: Media file")

        print(f"Format: {path.suffix.upper().lstrip('.')}")
        print(f"Size: {file_size:,} bytes")
        print("(Install 'ffmpeg' for detailed media analysis)")

    @classmethod
    def priority(cls: type["MediaHandler"]) -> int:
        """Return the priority of the Media handler.

        Returns:
            55 (medium-high priority, between JSON and PDF).
        """
        return 55  # Media has priority between JSON and PDF
