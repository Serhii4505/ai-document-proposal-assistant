"""File-system, signature and archive safety checks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path, PurePosixPath
import zipfile

from app.ingestion.errors import (
    FileLimitError,
    UnsafePathError,
    UnsupportedFileError,
)


SUPPORTED_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
}


@dataclass(frozen=True, slots=True)
class IngestionLimits:
    max_file_bytes: int = 10 * 1024 * 1024
    max_archive_members: int = 5_000
    max_archive_uncompressed_bytes: int = 50 * 1024 * 1024
    max_archive_member_bytes: int = 20 * 1024 * 1024
    max_compression_ratio: int = 500
    max_pdf_pages: int = 500
    max_sheets: int = 50
    max_rows_per_sheet: int = 10_000
    max_columns_per_row: int = 100
    max_cell_characters: int = 50_000


@dataclass(frozen=True, slots=True)
class ValidatedFile:
    path: Path
    extension: str
    media_type: str
    size_bytes: int
    sha256: str


def _ensure_safe_archive(path: Path, extension: str, limits: IngestionLimits) -> None:
    required_member = "word/document.xml" if extension == ".docx" else "xl/workbook.xml"
    try:
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if len(members) > limits.max_archive_members:
                raise FileLimitError("Archive contains too many members")

            total_uncompressed = 0
            names: set[str] = set()
            for member in members:
                member_path = PurePosixPath(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise UnsafePathError("Archive contains an unsafe member path")
                if member.flag_bits & 0x1:
                    raise UnsupportedFileError("Encrypted Office files are not supported")
                if member.file_size > limits.max_archive_member_bytes:
                    raise FileLimitError("Archive member is too large")
                if member.file_size and member.compress_size == 0:
                    raise FileLimitError("Archive has an invalid compression ratio")
                if member.compress_size and member.file_size / member.compress_size > limits.max_compression_ratio:
                    raise FileLimitError("Archive compression ratio is too high")

                total_uncompressed += member.file_size
                if total_uncompressed > limits.max_archive_uncompressed_bytes:
                    raise FileLimitError("Archive expands beyond the allowed size")
                names.add(member.filename)

            if "[Content_Types].xml" not in names or required_member not in names:
                raise UnsupportedFileError(f"File content does not match {extension}")
    except zipfile.BadZipFile as exc:
        raise UnsupportedFileError(f"File content does not match {extension}") from exc


def validate_file(
    path: Path,
    *,
    allowed_root: Path,
    limits: IngestionLimits,
) -> ValidatedFile:
    """Validate location, name, size, extension, signature and archive structure."""

    candidate = Path(path)
    root = Path(allowed_root).resolve(strict=True)

    if candidate.is_symlink():
        raise UnsafePathError("Symbolic links are not allowed")

    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise UnsafePathError("Input file does not exist") from exc

    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise UnsafePathError("Input file is outside the approved directory") from exc

    if not resolved.is_file():
        raise UnsafePathError("Input path must be a regular file")
    if len(resolved.name) > 255 or any(ord(char) < 32 for char in resolved.name):
        raise UnsafePathError("Input filename is unsafe")

    extension = resolved.suffix.lower()
    if extension not in SUPPORTED_TYPES:
        raise UnsupportedFileError("Supported file types are PDF, DOCX, XLSX and CSV")

    size_bytes = resolved.stat().st_size
    if size_bytes == 0:
        raise FileLimitError("Input file is empty")
    if size_bytes > limits.max_file_bytes:
        raise FileLimitError("Input file exceeds the allowed size")

    with resolved.open("rb") as stream:
        signature = stream.read(8)
        digest = hashlib.sha256(signature)
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)

    if extension == ".pdf" and not signature.startswith(b"%PDF-"):
        raise UnsupportedFileError("File content does not match .pdf")
    if extension in {".docx", ".xlsx"}:
        if not signature.startswith(b"PK"):
            raise UnsupportedFileError(f"File content does not match {extension}")
        _ensure_safe_archive(resolved, extension, limits)
    if extension == ".csv" and b"\x00" in signature:
        raise UnsupportedFileError("CSV file contains binary data")

    return ValidatedFile(
        path=resolved,
        extension=extension,
        media_type=SUPPORTED_TYPES[extension],
        size_bytes=size_bytes,
        sha256=digest.hexdigest(),
    )

