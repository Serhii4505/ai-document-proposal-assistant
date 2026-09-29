"""Expected RAG pipeline failures."""


class RAGError(RuntimeError):
    """Base class for retrieval failures."""


class EmbeddingProviderError(RAGError):
    """Embedding generation failed or returned invalid data."""


class VectorStoreError(RAGError):
    """Stored vectors are invalid or incompatible."""


class InsufficientEvidenceError(RAGError):
    """No retrieved source meets the configured evidence threshold."""

