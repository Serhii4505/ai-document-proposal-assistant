"""Persistent SQLite vector storage for the local portfolio demo."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3
from uuid import UUID

from app.ingestion.models import DocumentChunk
from app.rag.errors import VectorStoreError
from app.rag.models import RetrievalMatch


VECTOR_SCHEMA = """
CREATE TABLE IF NOT EXISTS vector_entries (
    chunk_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    text TEXT NOT NULL,
    location TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    embedding_json TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    embedding_model TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vectors_document ON vector_entries(document_id);
CREATE INDEX IF NOT EXISTS idx_vectors_model ON vector_entries(embedding_model, dimension);
"""


def _unit_vector(values: list[float]) -> list[float]:
    if not values or any(not math.isfinite(value) for value in values):
        raise VectorStoreError("Vector is empty or contains invalid values")
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        raise VectorStoreError("Vector has zero magnitude")
    return [value / norm for value in values]


class SQLiteVectorStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(VECTOR_SCHEMA)

    def replace_document(
        self,
        document_id: UUID,
        chunks: list[DocumentChunk],
        vectors: list[list[float]],
        *,
        embedding_model: str,
    ) -> None:
        if not chunks or len(chunks) != len(vectors):
            raise VectorStoreError("Chunks and vectors must be non-empty and have equal length")
        normalized = [_unit_vector(vector) for vector in vectors]
        dimension = len(normalized[0])
        if any(len(vector) != dimension for vector in normalized):
            raise VectorStoreError("All embeddings must have the same dimension")

        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM vector_entries WHERE document_id = ?", (str(document_id),))
            connection.executemany(
                """
                INSERT INTO vector_entries (
                    chunk_id, document_id, text, location, metadata_json,
                    embedding_json, dimension, embedding_model, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        str(document_id),
                        chunk.text,
                        chunk.location,
                        json.dumps(chunk.metadata, ensure_ascii=False, sort_keys=True),
                        json.dumps(vector),
                        dimension,
                        embedding_model,
                        created_at,
                    )
                    for chunk, vector in zip(chunks, normalized, strict=True)
                ],
            )
            connection.commit()

    def search(
        self,
        query_vector: list[float],
        *,
        embedding_model: str,
        top_k: int = 5,
    ) -> list[RetrievalMatch]:
        if top_k < 1 or top_k > 50:
            raise ValueError("top_k must be between 1 and 50")
        query = _unit_vector(query_vector)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM vector_entries WHERE embedding_model = ? AND dimension = ?",
                (embedding_model, len(query)),
            ).fetchall()

        matches: list[RetrievalMatch] = []
        for row in rows:
            try:
                vector = [float(value) for value in json.loads(row["embedding_json"])]
                metadata = json.loads(row["metadata_json"])
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                raise VectorStoreError("Stored vector record is corrupt") from exc
            if len(vector) != len(query):
                continue
            score = sum(left * right for left, right in zip(query, vector, strict=True))
            matches.append(
                RetrievalMatch(
                    chunk_id=row["chunk_id"],
                    document_id=UUID(row["document_id"]),
                    text=row["text"],
                    location=row["location"],
                    metadata=metadata,
                    score=max(-1.0, min(1.0, score)),
                )
            )
        return sorted(matches, key=lambda match: (-match.score, match.chunk_id))[:top_k]

