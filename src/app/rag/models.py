"""Validated RAG records."""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.domain import StrictModel


class RetrievalMatch(StrictModel):
    chunk_id: str
    document_id: UUID
    text: str = Field(min_length=1)
    location: str = Field(min_length=1)
    metadata: dict[str, str] = Field(default_factory=dict)
    score: float = Field(ge=-1.0, le=1.0)


class RetrievalResult(StrictModel):
    query: str = Field(min_length=1)
    matches: list[RetrievalMatch] = Field(min_length=1)
    context: str = Field(min_length=1)

