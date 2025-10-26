import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from l_command.handlers.archive import ArchiveHandler

if TYPE_CHECKING:
    from pytest_mock import MockerFixture  # type: ignore[import]


def test_can_handle_zip(tmp_path: Path) -> None:
    """Test ArchiveHandler can detect ZIP files."""
    zip_file = tmp_path / "test.zip"

    # Create a real ZIP file
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("test.txt", "test content")

    assert ArchiveHandler.can_handle(zip_file) is True


def test_can_handle_tar(tmp_path: Path) -> None:
    """Test ArchiveHandler can detect TAR files."""
    tar_file = tmp_path / "test.tar"

    # Create a real TAR file
    with tarfile.open(tar_file, "w") as tf:
        temp_file = tmp_path / "temp.txt"
        temp_file.write_text("content")
        tf.add(temp_file, arcname="temp.txt")

    assert ArchiveHandler.can_handle(tar_file) is True


def test_can_handle_tgz(tmp_path: Path) -> None:
    """Test ArchiveHandler can detect compressed TAR files."""
    tgz_file = tmp_path / "test.tgz"

    # Create a real TAR.GZ file
    with tarfile.open(tgz_file, "w:gz") as tf:
        temp_file = tmp_path / "temp.txt"
        temp_file.write_text("content")
        tf.add(temp_file, arcname="temp.txt")

    assert ArchiveHandler.can_handle(tgz_file) is True


def test_can_handle_invalid(tmp_path: Path) -> None:
    """Test ArchiveHandler rejects non-archive files."""
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("not an archive")

    assert ArchiveHandler.can_handle(txt_file) is False


def test_handle_zip(mocker: "MockerFixture") -> None:
    path = Path("test.zip")
    mocker.patch("shutil.which", return_value="/usr/bin/unzip")
    mock_popen = mocker.patch("l_command.handlers.archive.subprocess.Popen")
    mock_pager = mocker.patch("l_command.handlers.archive.smart_pager")

    ArchiveHandler.handle(path)

    mock_popen.assert_called_with(
        ["unzip", "-l", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    mock_pager.assert_called_once()


def test_handle_tar(mocker: "MockerFixture") -> None:
    path = Path("test.tar")
    mocker.patch("shutil.which", return_value="/usr/bin/tar")
    mock_popen = mocker.patch("l_command.handlers.archive.subprocess.Popen")
    mock_pager = mocker.patch("l_command.handlers.archive.smart_pager")

    ArchiveHandler.handle(path)

    mock_popen.assert_called_with(
        ["tar", "-tvf", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    mock_pager.assert_called_once()


def test_can_handle_jar(tmp_path: Path) -> None:
    """Test ArchiveHandler can detect JAR files (ZIP variant)."""
    jar_file = tmp_path / "test.jar"

    # Create a real JAR file (same as ZIP)
    with zipfile.ZipFile(jar_file, "w") as zf:
        zf.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\n")

    assert ArchiveHandler.can_handle(jar_file) is True


def test_can_handle_tar_zst(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test ArchiveHandler can detect TAR.ZST files."""
    tar_zst_file = tmp_path / "test.tar.zst"

    # Create a fake tar.zst file (just for extension check)
    tar_zst_file.write_bytes(b"\x28\xb5\x2f\xfd")  # Zstandard magic bytes

    mocker.patch("shutil.which", side_effect=lambda cmd: "/usr/bin/" + cmd if cmd in ["tar", "unzstd"] else None)
    assert ArchiveHandler.can_handle(tar_zst_file) is True


def test_handle_jar(mocker: "MockerFixture") -> None:
    path = Path("test.jar")
    mocker.patch("shutil.which", return_value="/usr/bin/unzip")
    mock_popen = mocker.patch("l_command.handlers.archive.subprocess.Popen")
    mock_pager = mocker.patch("l_command.handlers.archive.smart_pager")

    ArchiveHandler.handle(path)

    mock_popen.assert_called_with(
        ["unzip", "-l", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    mock_pager.assert_called_once()


def test_handle_tar_zst(mocker: "MockerFixture") -> None:
    path = Path("test.tar.zst")
    mocker.patch("shutil.which", side_effect=["/usr/bin/tar", "/usr/bin/unzstd"])
    mock_popen = mocker.patch("l_command.handlers.archive.subprocess.Popen")
    mock_pager = mocker.patch("l_command.handlers.archive.smart_pager")

    ArchiveHandler.handle(path)

    mock_popen.assert_called_with(
        ["tar", "--use-compress-program=unzstd", "-tvf", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    mock_pager.assert_called_once()


def test_handle_zip_with_less(mocker: "MockerFixture") -> None:
    path = Path("test.zip")
    mocker.patch("shutil.which", return_value="/usr/bin/unzip")

    # Create a mock process
    mock_process = mocker.Mock()
    mock_process.stdout = mocker.Mock()
    mocker.patch("l_command.handlers.archive.subprocess.Popen", return_value=mock_process)

    # Mock the smart_pager function
    mock_pager = mocker.patch("l_command.handlers.archive.smart_pager")

    ArchiveHandler.handle(path)

    # Verify smart_pager was called with the process and less command
    mock_pager.assert_called_with(mock_process, ["less", "-R"])


def test_handle_tar_with_less(mocker: "MockerFixture") -> None:
    path = Path("test.tar")
    mocker.patch("shutil.which", side_effect=["/usr/bin/tar", "/usr/bin/unzstd"])

    # Create a mock process
    mock_process = mocker.Mock()
    mock_process.stdout = mocker.Mock()
    mocker.patch("l_command.handlers.archive.subprocess.Popen", return_value=mock_process)

    # Mock the smart_pager function
    mock_pager = mocker.patch("l_command.handlers.archive.smart_pager")

    ArchiveHandler.handle(path)

    # Verify smart_pager was called with the process and less command
    mock_pager.assert_called_with(mock_process, ["less", "-R"])
