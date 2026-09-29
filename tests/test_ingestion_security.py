from pathlib import Path
import zipfile

import pytest
from pypdf import PdfWriter

from app.ingestion import DocumentIngestionService
from app.ingestion.errors import (
    EmptyDocumentError,
    FileLimitError,
    UnsafePathError,
    UnsupportedFileError,
)
from app.ingestion.security import IngestionLimits


def test_rejects_file_outside_approved_root(tmp_path: Path) -> None:
    approved = tmp_path / "approved"
    approved.mkdir()
    outside = tmp_path / "outside.csv"
    outside.write_text("code,name\nA1,Service\n", encoding="utf-8")

    with pytest.raises(UnsafePathError, match="outside"):
        DocumentIngestionService(approved).ingest(outside)


def test_rejects_symbolic_link(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    source.write_text("code,name\nA1,Service\n", encoding="utf-8")
    link = tmp_path / "link.csv"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("Symbolic links are unavailable in this environment")

    with pytest.raises(UnsafePathError, match="Symbolic"):
        DocumentIngestionService(tmp_path).ingest(link)


def test_rejects_unsupported_extension(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("not supported", encoding="utf-8")

    with pytest.raises(UnsupportedFileError, match="Supported file types"):
        DocumentIngestionService(tmp_path).ingest(path)


def test_rejects_extension_signature_mismatch(tmp_path: Path) -> None:
    path = tmp_path / "fake.pdf"
    path.write_text("This is not a PDF", encoding="utf-8")

    with pytest.raises(UnsupportedFileError, match="does not match"):
        DocumentIngestionService(tmp_path).ingest(path)


def test_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.touch()

    with pytest.raises(FileLimitError, match="empty"):
        DocumentIngestionService(tmp_path).ingest(path)


def test_rejects_file_over_configured_limit(tmp_path: Path) -> None:
    path = tmp_path / "large.csv"
    path.write_text("code,description\nA1," + "x" * 100, encoding="utf-8")
    limits = IngestionLimits(max_file_bytes=32)

    with pytest.raises(FileLimitError, match="allowed size"):
        DocumentIngestionService(tmp_path, limits=limits).ingest(path)


def test_rejects_binary_or_non_utf8_csv(tmp_path: Path) -> None:
    path = tmp_path / "binary.csv"
    path.write_bytes("code,name\nA1,Service".encode("utf-16"))

    with pytest.raises(UnsupportedFileError):
        DocumentIngestionService(tmp_path).ingest(path)


def test_rejects_archive_path_traversal(tmp_path: Path) -> None:
    path = tmp_path / "malicious.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<document />")
        archive.writestr("../escape.txt", "unsafe")

    with pytest.raises(UnsafePathError, match="(?i)archive"):
        DocumentIngestionService(tmp_path).ingest(path)


def test_rejects_office_file_with_wrong_internal_type(tmp_path: Path) -> None:
    path = tmp_path / "fake.xlsx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", "<document />")

    with pytest.raises(UnsupportedFileError, match="does not match"):
        DocumentIngestionService(tmp_path).ingest(path)


def test_rejects_pdf_without_extractable_text(tmp_path: Path) -> None:
    path = tmp_path / "scan.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    with path.open("wb") as stream:
        writer.write(stream)

    with pytest.raises(EmptyDocumentError, match="OCR is not enabled"):
        DocumentIngestionService(tmp_path).ingest(path)


def test_rejects_csv_over_row_limit(tmp_path: Path) -> None:
    path = tmp_path / "rows.csv"
    path.write_text("code,name\nA1,One\nA2,Two\n", encoding="utf-8")
    limits = IngestionLimits(max_rows_per_sheet=2)

    with pytest.raises(FileLimitError, match="too many rows"):
        DocumentIngestionService(tmp_path, limits=limits).ingest(path)
