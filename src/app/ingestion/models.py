"""Validated records produced by document ingestion."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.domain import StrictModel


class SourceSegment(StrictModel):
    text: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=300)
    metadata: dict[str, str] = Field(default_factory=dict)


class DocumentChunk(StrictModel):
    chunk_id: str = Field(min_length=16, max_length=64)
    document_id: UUID
    index: int = Field(ge=0)
    text: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=300)
    metadata: dict[str, str] = Field(default_factory=dict)


class DocumentMetadata(StrictModel):
    document_id: UUID
    filename: str = Field(min_length=1, max_length=255)
    extension: str
    media_type: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parser: str
    segment_count: int = Field(gt=0)
    chunk_count: int = Field(gt=0)
    ingested_at: datetime


class IngestedDocument(StrictModel):
    metadata: DocumentMetadata
    segments: list[SourceSegment] = Field(min_length=1)
    chunks: list[DocumentChunk] = Field(min_length=1)

