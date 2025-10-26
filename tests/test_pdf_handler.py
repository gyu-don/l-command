"""
Tests for PDFHandler.
"""

import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from l_command.handlers.pdf import PDFHandler

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from pytest_mock import MockerFixture


def test_can_handle_pdf_extension() -> None:
    """Test PDF handler detection by extension."""
    # PDF file with .pdf extension
    with tempfile.NamedTemporaryFile(suffix=".pdf", mode="wb") as tmp:
        tmp.write(b"%PDF-1.4\n%dummy content")  # Write minimal PDF header
        tmp.flush()
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is True

    # PDF file with .PDF extension (uppercase)
    with tempfile.NamedTemporaryFile(suffix=".PDF", mode="wb") as tmp:
        tmp.write(b"%PDF-1.5\n%dummy content")
        tmp.flush()
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is True

    # Empty PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is False

    # Non-PDF extension
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is False


def test_can_handle_pdf_content() -> None:
    """Test PDF handler detection by content."""
    # PDF content with magic bytes
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb") as tmp:
        tmp.write(b"%PDF-1.4\n%dummy content")
        tmp.flush()
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is True

    # Non-PDF content
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="wb") as tmp:
        tmp.write(b"This is not a PDF")
        tmp.flush()
        path = Path(tmp.name)
        assert PDFHandler.can_handle(path) is False


def test_priority() -> None:
    """Test PDF handler priority."""
    assert PDFHandler.priority() == 60


def test_handle_empty_pdf(tmp_path: Path, capsys: "CaptureFixture") -> None:
    """Test handling empty PDF file."""
    pdf_file = tmp_path / "empty.pdf"
    pdf_file.touch()

    PDFHandler.handle(pdf_file)

    captured = capsys.readouterr()
    assert "(Empty PDF file)" in captured.out


def test_handle_pdf_size_exceeds_limit(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling PDF file that exceeds size limit."""
    from l_command.handlers.pdf import MAX_PDF_SIZE_BYTES

    pdf_file = tmp_path / "large.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%content")

    # Mock stat to return size over limit
    mock_stat = mocker.patch("pathlib.Path.stat")
    mock_stat_result = mocker.Mock()
    mock_stat_result.st_size = MAX_PDF_SIZE_BYTES + 1
    mock_stat.return_value = mock_stat_result

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    PDFHandler.handle(pdf_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(pdf_file)


def test_handle_pdf_with_pdfminer(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling PDF with pdfminer.six (extractable text)."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%content")

    # Mock pdfminer module
    mock_pdfminer = mocker.Mock()
    mock_extract = mocker.Mock(return_value="This is extracted text from PDF.\nLine 2\nLine 3")
    mock_pdfminer.high_level.extract_text = mock_extract

    mocker.patch.dict("sys.modules", {"pdfminer": mock_pdfminer, "pdfminer.high_level": mock_pdfminer.high_level})

    PDFHandler.handle(pdf_file)

    # Verify extract_text was called
    mock_extract.assert_called_once_with(str(pdf_file))

    # Verify output contains PDF info and text
    captured = capsys.readouterr()
    assert "PDF File:" in captured.out
    assert "Size:" in captured.out
    assert "This is extracted text from PDF" in captured.out


def test_handle_pdf_with_long_text_uses_pager(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling PDF with long text (uses pager)."""
    pdf_file = tmp_path / "long.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%content")

    # Mock pdfminer to return long text
    long_text = "\n".join([f"Line {i}" for i in range(50)])
    mock_pdfminer = mocker.Mock()
    mock_extract = mocker.Mock(return_value=long_text)
    mock_pdfminer.high_level.extract_text = mock_extract

    mocker.patch.dict("sys.modules", {"pdfminer": mock_pdfminer, "pdfminer.high_level": mock_pdfminer.high_level})

    # Mock subprocess.Popen for pager
    mock_popen = mocker.patch("subprocess.Popen")
    mock_process = mocker.Mock()
    mock_process.stdin = mocker.Mock()
    mock_popen.return_value = mock_process

    PDFHandler.handle(pdf_file)

    # Verify pager was used (less -RFX)
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert args[0] == "less"
    assert "-RFX" in args


def test_handle_pdf_no_extractable_text(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling PDF with no extractable text."""
    pdf_file = tmp_path / "no_text.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%content")

    # Mock pdfminer to return empty string
    mock_pdfminer = mocker.Mock()
    mock_extract = mocker.Mock(return_value="")
    mock_pdfminer.high_level.extract_text = mock_extract

    mocker.patch.dict("sys.modules", {"pdfminer": mock_pdfminer, "pdfminer.high_level": mock_pdfminer.high_level})

    PDFHandler.handle(pdf_file)

    captured = capsys.readouterr()
    assert "PDF File:" in captured.out
    assert "(No extractable text content)" in captured.out


def test_handle_pdf_pdfminer_not_available(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling PDF when pdfminer.six is not installed."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%content")

    # Mock ImportError for pdfminer
    def mock_import(name: str, *args: object, **kwargs: object) -> object:
        if "pdfminer" in name:
            raise ImportError("No module named 'pdfminer'")
        return __import__(name, *args, **kwargs)

    mocker.patch("builtins.__import__", side_effect=mock_import)

    PDFHandler.handle(pdf_file)

    captured = capsys.readouterr()
    assert "PDF File:" in captured.out
    assert "Install pdfminer.six for text extraction" in captured.out


def test_handle_pdf_extraction_error(tmp_path: Path, mocker: "MockerFixture", capsys: "CaptureFixture") -> None:
    """Test handling PDF when extraction fails."""
    pdf_file = tmp_path / "corrupted.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%corrupted")

    # Mock pdfminer to raise exception
    mock_pdfminer = mocker.Mock()
    mock_extract = mocker.Mock(side_effect=Exception("PDF parsing error"))
    mock_pdfminer.high_level.extract_text = mock_extract

    mocker.patch.dict("sys.modules", {"pdfminer": mock_pdfminer, "pdfminer.high_level": mock_pdfminer.high_level})

    PDFHandler.handle(pdf_file)

    captured = capsys.readouterr()
    assert "PDF File:" in captured.out
    assert "(Error extracting text content)" in captured.out


def test_handle_pdf_os_error(tmp_path: Path, mocker: "MockerFixture") -> None:
    """Test handling PDF with OS error."""
    pdf_file = tmp_path / "error.pdf"
    pdf_file.write_bytes(b"%PDF-1.4\n%content")

    # Mock stat to raise OSError
    mocker.patch.object(Path, "stat", side_effect=OSError("Permission denied"))

    # Mock DefaultFileHandler
    mock_default = mocker.patch("l_command.handlers.default.DefaultFileHandler.handle")

    PDFHandler.handle(pdf_file)

    # Should fall back to default handler
    mock_default.assert_called_once_with(pdf_file)
