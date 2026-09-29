"""Explicit, user-safe ingestion errors."""


class IngestionError(ValueError):
    """Base class for expected document ingestion failures."""


class UnsafePathError(IngestionError):
    """The selected file is outside the approved input directory."""


class UnsupportedFileError(IngestionError):
    """The file type is not supported or does not match its content."""


class FileLimitError(IngestionError):
    """A configured safety limit was exceeded."""


class CorruptDocumentError(IngestionError):
    """The file cannot be parsed as its declared document type."""


class EmptyDocumentError(IngestionError):
    """The document contains no extractable text."""

