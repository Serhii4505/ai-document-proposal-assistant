"""Deterministic, source-preserving text chunking."""

from __future__ import annotations

import hashlib
from uuid import UUID

from app.ingestion.models import DocumentChunk, SourceSegment


def _split_text(text: str, target_characters: int, overlap_characters: int) -> list[str]:
    if len(text) <= target_characters:
        return [text]

    parts: list[str] = []
    start = 0
    while start < len(text):
        preferred_end = min(start + target_characters, len(text))
        end = preferred_end
        if preferred_end < len(text):
            boundary = text.rfind(" ", start + target_characters // 2, preferred_end)
            if boundary > start:
                end = boundary
        chunk = text[start:end].strip()
        if chunk:
            parts.append(chunk)
        if end >= len(text):
            break
        next_start = max(end - overlap_characters, start + 1)
        while next_start < end and not text[next_start].isspace():
            next_start += 1
        start = next_start
    return parts


def create_chunks(
    document_id: UUID,
    segments: list[SourceSegment],
    *,
    target_characters: int = 1_200,
    overlap_characters: int = 150,
) -> list[DocumentChunk]:
    if target_characters < 200:
        raise ValueError("target_characters must be at least 200")
    if overlap_characters < 0 or overlap_characters >= target_characters:
        raise ValueError("overlap_characters must be non-negative and smaller than target")

    chunks: list[DocumentChunk] = []
    for segment in segments:
        for text in _split_text(segment.text, target_characters, overlap_characters):
            index = len(chunks)
            digest = hashlib.sha256(
                f"{document_id}:{index}:{segment.location}:{text}".encode("utf-8")
            ).hexdigest()[:32]
            chunks.append(
                DocumentChunk(
                    chunk_id=digest,
                    document_id=document_id,
                    index=index,
                    text=text,
                    location=segment.location,
                    metadata=segment.metadata,
                )
            )
    return chunks

