import os
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
    mock_run = mocker.patch("l_command.handlers.archive.subprocess.run")
    ArchiveHandler.handle(path)
    mock_run.assert_called_with(["unzip", "-l", str(path)], check=True)


def test_handle_tar(mocker: "MockerFixture") -> None:
    path = Path("test.tar")
    mocker.patch("shutil.which", return_value="/usr/bin/tar")
    mock_run = mocker.patch("l_command.handlers.archive.subprocess.run")
    ArchiveHandler.handle(path)
    mock_run.assert_called_with(["tar", "-tvf", str(path)], check=True)


def test_can_handle_jar() -> None:
    path = Path("test.jar")
    assert ArchiveHandler.can_handle(path) is True


def test_can_handle_tar_zst() -> None:
    path = Path("test.tar.zst")
    assert ArchiveHandler.can_handle(path) is True


def test_handle_jar(mocker: "MockerFixture") -> None:
    path = Path("test.jar")
    mocker.patch("shutil.which", return_value="/usr/bin/unzip")
    mocker.patch("l_command.handlers.archive.subprocess.run")
    ArchiveHandler.handle(path)
    subprocess.run.assert_called_with(["unzip", "-l", str(path)], check=True)


def test_handle_tar_zst(mocker: "MockerFixture") -> None:
    path = Path("test.tar.zst")
    mocker.patch("shutil.which", side_effect=["/usr/bin/tar", "/usr/bin/unzstd"])
    mocker.patch("l_command.handlers.archive.subprocess.run")
    ArchiveHandler.handle(path)
    subprocess.run.assert_called_with(["tar", "--use-compress-program=unzstd", "-tvf", str(path)], check=True)


def test_handle_zip_with_less(mocker: "MockerFixture") -> None:
    path = Path("test.zip")
    mocker.patch("shutil.which", return_value="/usr/bin/unzip")
    mocker.patch("os.get_terminal_size", return_value=os.terminal_size((80, 24)))
    mock_run = mocker.patch("l_command.handlers.archive.subprocess.run")

    mock_process = mocker.Mock()
    mock_stdout = mocker.Mock()
    mock_stdout.__iter__ = lambda self: iter([b"line\n"] * 50)  # Simulate 50 lines of output
    mock_process.stdout = mock_stdout
    mock_process.communicate.return_value = (b"line\n" * 50, None)
    mocker.patch("l_command.handlers.archive.subprocess.Popen", return_value=mock_process)

    ArchiveHandler.handle(path)

    mock_run.assert_called_with(["less", "-R"], stdin=mock_stdout, check=True)


def test_handle_tar_with_less(mocker: "MockerFixture") -> None:
    path = Path("test.tar")
    mocker.patch("shutil.which", side_effect=["/usr/bin/tar", "/usr/bin.unzstd"])
    mocker.patch("os.get_terminal_size", return_value=os.terminal_size((80, 24)))
    mock_run = mocker.patch("l_command.handlers.archive.subprocess.run")

    mock_process = mocker.Mock()
    mock_stdout = mocker.Mock()
    mock_stdout.__iter__ = lambda self: iter([b"line\n"] * 50)  # Simulate 50 lines of output
    mock_process.stdout = mock_stdout
    mock_process.communicate.return_value = (b"line\n" * 50, None)
    mocker.patch("l_command.handlers.archive.subprocess.Popen", return_value=mock_process)

    ArchiveHandler.handle(path)

    mock_run.assert_called_with(["less", "-R"], stdin=mock_stdout, check=True)
