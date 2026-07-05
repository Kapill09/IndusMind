from typing import Any, TypedDict

from backend.services.embedding_service import EmbeddingService, EmbeddingServiceError
from backend.services.vectordb_service import (
    VectorDBService,
    VectorDBServiceError,
    VectorSearchResult,
)


class RetrievalResult(TypedDict):
    """One semantic retrieval result returned to API callers."""

    chunk_id: str
    text: str
    page_start: int | None
    page_end: int | None
    metadata: dict[str, Any]

    # Raw distance returned by ChromaDB.
    distance: float | None

    # Human-friendly relevance score (0–1).
    score: float


class RetrievalResponse(TypedDict):
    """Structured response returned for a retrieval request."""

    question: str
    results: list[RetrievalResult]


class RetrievalServiceError(Exception):
    """Base exception for all retrieval service errors."""


class RetrievalValidationError(RetrievalServiceError):
    """Raised when the retrieval request is invalid."""


class RetrievalEmbeddingError(RetrievalServiceError):
    """Raised when the question embedding cannot be generated."""


class RetrievalSearchError(RetrievalServiceError):
    """Raised when semantic search cannot be completed."""


class RetrievalService:
    """Retrieve relevant INDUS MIND document chunks for a user question.

    Responsibilities
    ----------------
    1. Validate the user's question.
    2. Generate a semantic embedding using EmbeddingService.
    3. Search ChromaDB using VectorDBService.
    4. Return the most relevant chunks.

    This service DOES NOT:
    - Call an LLM
    - Build prompts
    - Generate answers
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vectordb_service: VectorDBService,
    ) -> None:
        self.embedding_service = embedding_service
        self.vectordb_service = vectordb_service

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
    ) -> RetrievalResponse:
        """Retrieve the top K semantically relevant chunks."""

        clean_question = self._validate_question(question)
        clean_top_k = self._validate_top_k(top_k)

        try:
            # Generate embedding for the user question.
            question_embedding = self.embedding_service.generate_embedding(
                clean_question
            )

        except EmbeddingServiceError as exc:
            raise RetrievalEmbeddingError(
                "Failed to generate question embedding."
            ) from exc

        try:
            # Perform semantic similarity search.
            search_results = self.vectordb_service.search(
                query_embedding=question_embedding,
                top_k=clean_top_k,
            )

        except VectorDBServiceError as exc:
            raise RetrievalSearchError(
                "Failed to retrieve relevant chunks."
            ) from exc

        return {
            "question": clean_question,
            "results": [
                self._format_result(result)
                for result in search_results
            ],
        }

    @staticmethod
    def _validate_question(question: str) -> str:
        """Validate and normalize the user question."""

        if not isinstance(question, str):
            raise RetrievalValidationError(
                "Question must be a string."
            )

        clean_question = question.strip()

        if not clean_question:
            raise RetrievalValidationError(
                "Question cannot be empty."
            )

        return clean_question

    @staticmethod
    def _validate_top_k(top_k: int) -> int:
        """Validate requested number of retrieval results."""

        if not isinstance(top_k, int):
            raise RetrievalValidationError(
                "top_k must be an integer."
            )

        if top_k <= 0:
            raise RetrievalValidationError(
                "top_k must be greater than 0."
            )

        if top_k > 20:
            raise RetrievalValidationError(
                "top_k cannot exceed 20."
            )

        return top_k

    @staticmethod
    def _format_result(
        result: VectorSearchResult,
    ) -> RetrievalResult:
        """Convert a ChromaDB search result into a retrieval response."""

        metadata = dict(result.get("metadata") or {})
        distance = result.get("distance")

        return {
            "chunk_id": result["chunk_id"],
            "text": result["text"],
            "page_start": RetrievalService._metadata_int(
                metadata.get("page_start")
            ),
            "page_end": RetrievalService._metadata_int(
                metadata.get("page_end")
            ),
            "metadata": metadata,
            "distance": float(distance) if distance is not None else None,
            "score": RetrievalService._distance_to_score(distance),
        }

    @staticmethod
    def _distance_to_score(
        distance: float | None,
    ) -> float:
        """Convert Chroma distance into a human-friendly relevance score."""

        if distance is None:
            return 0.0

        # ChromaDB returns smaller distances for more relevant chunks.
        # Convert them into a 0–1 score where higher is better.
        return round(
            1.0 / (1.0 + max(float(distance), 0.0)),
            4,
        )

    @staticmethod
    def _metadata_int(value: Any) -> int | None:
        """Safely convert metadata values into integers."""

        if value is None or value == -1:
            return None

        try:
            return int(value)

        except (TypeError, ValueError):
            return None