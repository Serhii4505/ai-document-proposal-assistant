"""Orchestrates validation, parsing, normalization metadata and chunking."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from app.ingestion.chunking import create_chunks
from app.ingestion.errors import EmptyDocumentError
from app.ingestion.models import DocumentMetadata, IngestedDocument
from app.ingestion.parsers import parse_document
from app.ingestion.security import IngestionLimits, validate_file


class DocumentIngestionService:
    def __init__(
        self,
        allowed_root: Path,
        *,
        limits: IngestionLimits | None = None,
        target_chunk_characters: int = 1_200,
        chunk_overlap_characters: int = 150,
    ) -> None:
        self.allowed_root = Path(allowed_root)
        self.limits = limits or IngestionLimits()
        self.target_chunk_characters = target_chunk_characters
        self.chunk_overlap_characters = chunk_overlap_characters

    def ingest(self, path: Path) -> IngestedDocument:
        validated = validate_file(
            path,
            allowed_root=self.allowed_root,
            limits=self.limits,
        )
        parser_name, segments = parse_document(validated, self.limits)
        if not segments:
            raise EmptyDocumentError("Document contains no extractable text; OCR is not enabled")

        document_id = uuid5(NAMESPACE_URL, f"sha256:{validated.sha256}")
        chunks = create_chunks(
            document_id,
            segments,
            target_characters=self.target_chunk_characters,
            overlap_characters=self.chunk_overlap_characters,
        )
        chunks = [
            chunk.model_copy(
                update={
                    "metadata": {
                        **chunk.metadata,
                        "filename": validated.path.name,
                        "extension": validated.extension,
                    }
                }
            )
            for chunk in chunks
        ]
        if not chunks:
            raise EmptyDocumentError("Document contains no text suitable for indexing")

        metadata = DocumentMetadata(
            document_id=document_id,
            filename=validated.path.name,
            extension=validated.extension,
            media_type=validated.media_type,
            size_bytes=validated.size_bytes,
            sha256=validated.sha256,
            parser=parser_name,
            segment_count=len(segments),
            chunk_count=len(chunks),
            ingested_at=datetime.now(timezone.utc),
        )
        return IngestedDocument(metadata=metadata, segments=segments, chunks=chunks)
