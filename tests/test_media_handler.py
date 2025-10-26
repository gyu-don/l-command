"""
Tests for MediaHandler.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from l_command.handlers.media import MediaHandler

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from pytest_mock import MockerFixture


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


def test_handle_empty_media(tmp_path: Path, capsys: "CaptureFixture") -> None:
    """Test handling empty media file."""
    media_file = tmp_path / "empty.mp4"
    media_file.touch()

    MediaHandler.handle(media_file)

    captured = capsys.readouterr()
    assert "(Empty media file)" in captured.out


def test_handle_media_size_exceeds_limit(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling media file that exceeds size limit."""
    from l_command.handlers.media import MAX_MEDIA_SIZE_BYTES

    media_file = tmp_path / "large.mp4"
    media_file.write_bytes(b"\x00\x00\x00\x20ftypmp42")

    # Mock stat to return size over limit
    mock_stat = mocker.patch("pathlib.Path.stat")
    mock_stat_result = mocker.Mock()
    mock_stat_result.st_size = MAX_MEDIA_SIZE_BYTES + 1
    mock_stat.return_value = mock_stat_result

    MediaHandler.handle(media_file)

    captured = capsys.readouterr()
    assert "Media File:" in captured.out
    assert "Install 'ffmpeg' for detailed media analysis" in captured.out


def test_handle_media_with_ffprobe(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling media file with ffprobe."""
    media_file = tmp_path / "test.mp4"
    media_file.write_bytes(b"\x00\x00\x00\x20ftypmp42")

    # Mock ffprobe output
    ffprobe_output = {
        "format": {
            "format_long_name": "QuickTime / MOV",
            "duration": "120.5",
            "bit_rate": "1500000",
        },
        "streams": [
            {
                "codec_type": "video",
                "codec_long_name": "H.264 / AVC",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
            },
            {
                "codec_type": "audio",
                "codec_long_name": "AAC (Advanced Audio Coding)",
                "sample_rate": "44100",
                "channels": 2,
            },
        ],
    }

    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = json.dumps(ffprobe_output)
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    MediaHandler.handle(media_file)

    # Verify ffprobe was called
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "ffprobe" in args[0]

    # Verify output
    captured = capsys.readouterr()
    assert "Media File:" in captured.out
    assert "Format: QuickTime / MOV" in captured.out
    assert "Duration: 02:00" in captured.out
    assert "Video Streams:" in captured.out
    assert "Audio Streams:" in captured.out


def test_handle_media_ffprobe_not_found(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling media when ffprobe is not available."""
    media_file = tmp_path / "test.mp3"
    media_file.write_bytes(b"ID3\x03\x00\x00\x00")

    # Mock ffprobe not found
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = FileNotFoundError("ffprobe not found")

    MediaHandler.handle(media_file)

    captured = capsys.readouterr()
    assert "Media File:" in captured.out
    assert "Type: Audio file" in captured.out
    assert "Install 'ffmpeg' for detailed media analysis" in captured.out


def test_handle_media_ffprobe_error(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling media when ffprobe fails."""
    media_file = tmp_path / "corrupted.mp4"
    media_file.write_bytes(b"\x00\x00\x00\x20ftypmp42")

    # Mock ffprobe failure
    mock_run = mocker.patch("subprocess.run")
    mock_run.side_effect = subprocess.CalledProcessError(1, ["ffprobe"], stderr="Invalid data")

    MediaHandler.handle(media_file)

    captured = capsys.readouterr()
    assert "Media File:" in captured.out
    assert "Install 'ffmpeg' for detailed media analysis" in captured.out


def test_handle_media_json_parse_error(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling media when ffprobe returns invalid JSON."""
    media_file = tmp_path / "test.mp4"
    media_file.write_bytes(b"\x00\x00\x00\x20ftypmp42")

    # Mock ffprobe with invalid JSON
    mock_run = mocker.patch("subprocess.run")
    mock_result = mocker.Mock()
    mock_result.stdout = "invalid json{"
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    MediaHandler.handle(media_file)

    captured = capsys.readouterr()
    assert "Media File:" in captured.out
    assert "Install 'ffmpeg' for detailed media analysis" in captured.out


def test_handle_media_os_error(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling media with OS error."""
    media_file = tmp_path / "error.mp4"
    media_file.write_bytes(b"\x00\x00\x00\x20ftypmp42")

    # Mock stat to raise OSError
    mocker.patch.object(Path, "stat", side_effect=OSError("Permission denied"))

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    MediaHandler.handle(media_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(media_file)


@patch("subprocess.run")
def test_ffprobe_timeout_handling(mock_run: MagicMock) -> None:
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
