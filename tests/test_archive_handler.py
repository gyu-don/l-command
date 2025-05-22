import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from l_command.handlers.archive import ArchiveHandler

if TYPE_CHECKING:
    from pytest_mock import MockerFixture  # type: ignore[import]


def test_can_handle_zip() -> None:
    path = Path("test.zip")
    assert ArchiveHandler.can_handle(path) is True


def test_can_handle_tar() -> None:
    path = Path("test.tar")
    assert ArchiveHandler.can_handle(path) is True


def test_can_handle_tgz() -> None:
    path = Path("test.tgz")
    assert ArchiveHandler.can_handle(path) is True


def test_can_handle_invalid() -> None:
    path = Path("test.txt")
    assert ArchiveHandler.can_handle(path) is False


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


def test_can_handle_jar() -> None:
    path = Path("test.jar")
    assert ArchiveHandler.can_handle(path) is True


def test_can_handle_tar_zst(mocker: "MockerFixture") -> None:
    path = Path("test.tar.zst")
    mocker.patch("shutil.which", side_effect=lambda cmd: "/usr/bin/" + cmd if cmd in ["tar", "unzstd"] else None)
    assert ArchiveHandler.can_handle(path) is True


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
