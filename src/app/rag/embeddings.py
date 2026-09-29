"""Replaceable embedding adapters for tests and Gemini."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import math
import re
from typing import Protocol

import httpx

from app.rag.errors import EmbeddingProviderError


class EmbeddingAdapter(Protocol):
    @property
    def model_name(self) -> str: ...

    def embed_documents(self, texts: Sequence[str], *, title: str) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _normalize(vector: list[float]) -> list[float]:
    if not vector or any(not math.isfinite(value) for value in vector):
        raise EmbeddingProviderError("Embedding contains invalid values")
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        raise EmbeddingProviderError("Embedding vector has zero magnitude")
    return [value / magnitude for value in vector]


class DeterministicEmbeddingAdapter:
    """Offline hashing-vectorizer used for repeatable tests without API quota."""

    def __init__(self, dimensions: int = 128) -> None:
        if dimensions < 16:
            raise ValueError("dimensions must be at least 16")
        self.dimensions = dimensions

    @property
    def model_name(self) -> str:
        return f"deterministic-hash-{self.dimensions}"

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[\w-]+", text.casefold())
        if not tokens:
            raise EmbeddingProviderError("Cannot embed empty text")
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[bucket] += sign
        return _normalize(vector)

    def embed_documents(self, texts: Sequence[str], *, title: str) -> list[list[float]]:
        del title
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class GeminiEmbeddingAdapter:
    """Gemini REST adapter. The API key is supplied at runtime and never stored."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gemini-embedding-2",
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Gemini API key is required")
        self.api_key = api_key
        self.model = model.removeprefix("models/")
        self.timeout_seconds = timeout_seconds
        self._client = client

    @property
    def model_name(self) -> str:
        return self.model

    def _embed(self, text: str) -> list[float]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
        }
        try:
            if self._client is not None:
                response = self._client.post(
                    url,
                    headers={"x-goog-api-key": self.api_key},
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            else:
                response = httpx.post(
                    url,
                    headers={"x-goog-api-key": self.api_key},
                    json=payload,
                    timeout=self.timeout_seconds,
                )
            response.raise_for_status()
            values = response.json()["embedding"]["values"]
            return _normalize([float(value) for value in values])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise EmbeddingProviderError("Gemini embedding request failed") from exc

    def embed_documents(self, texts: Sequence[str], *, title: str) -> list[list[float]]:
        safe_title = title.strip() or "none"
        return [self._embed(f"title: {safe_title} | text: {text}") for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(f"task: question answering | query: {text}")

