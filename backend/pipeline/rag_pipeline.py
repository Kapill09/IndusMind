from typing import Any, TypedDict

from backend.services.llm_service import LLMService, LLMServiceError
from backend.services.retrieval_service import RetrievalService, RetrievalServiceError


class RAGSource(TypedDict):
    """Source metadata included in the final RAG response."""

    chunk_id: str
    page_start: int | None
    page_end: int | None
    score: float | None
    metadata: dict[str, Any]


class RAGResponse(TypedDict):
    """Unified response returned by the RAG pipeline."""

    question: str
    answer: str
    retrieval: dict[str, Any]
    model: str
    sources: list[RAGSource]
    success: bool


class RAGPipelineError(Exception):
    """Base exception for all RAG pipeline errors."""


class RAGPipelineValidationError(RAGPipelineError):
    """Raised when a RAG request is invalid."""


class RAGPipelineRetrievalError(RAGPipelineError):
    """Raised when semantic retrieval fails."""


class RAGPipelineGenerationError(RAGPipelineError):
    """Raised when answer generation fails."""


class RAGPipeline:
    """Orchestrate retrieval and answer generation for INDUS MIND.

    The pipeline coordinates existing services only. It does not generate
    embeddings directly, access ChromaDB, parse PDFs, or call Gemini directly.
    RetrievalService owns semantic search, and LLMService owns answer
    generation from retrieved context.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
    ) -> None:
        # Services are injected so the orchestration layer remains easy to test
        # and each dependency keeps its own responsibility boundary.
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service

    def ask(self, question: str, top_k: int = 5) -> RAGResponse:
        """Answer a user question using retrieved document context.

        Args:
            question: User question to answer.
            top_k: Maximum number of chunks to retrieve before generation.

        Returns:
            A unified RAG response containing the answer, retrieval details,
            model name, cited sources, and success status.

        Raises:
            RAGPipelineValidationError: If the question or top_k is invalid.
            RAGPipelineRetrievalError: If RetrievalService fails.
            RAGPipelineGenerationError: If LLMService fails.
        """

        clean_question = self._validate_question(question)
        clean_top_k = self._validate_top_k(top_k)

        try:
            # RetrievalService handles embeddings and vector search through its
            # own dependencies; the pipeline only coordinates the call.
            retrieval = self.retrieval_service.retrieve(
                question=clean_question,
                top_k=clean_top_k,
            )
        except RetrievalServiceError as exc:
            raise RAGPipelineRetrievalError("Failed to retrieve context for the question.") from exc

        retrieved_chunks = retrieval.get("results", [])

        try:
            # LLMService receives the retrieved chunks and owns all prompt and
            # Gemini-specific answer generation behavior.
            llm_response = self.llm_service.generate_answer(
                question=retrieval["question"],
                retrieved_chunks=retrieved_chunks,
            )
        except LLMServiceError as exc:
            raise RAGPipelineGenerationError("Failed to generate an answer from retrieved context.") from exc

        return {
            "question": retrieval["question"],
            "answer": str(llm_response["answer"]),
            "retrieval": retrieval,

            "model": str(llm_response["model"]),
            
            "context_chunks": len(retrieved_chunks),
            
            "sources": self._build_sources(retrieved_chunks),
            
            "success": True,
        }

    @staticmethod
    def _validate_question(question: str) -> str:
        """Normalize and validate the user question before orchestration."""

        if not isinstance(question, str):
            raise RAGPipelineValidationError("question must be a string.")

        clean_question = question.strip()
        if not clean_question:
            raise RAGPipelineValidationError("question cannot be empty.")

        return clean_question

    @staticmethod
    def _validate_top_k(top_k: int) -> int:
        """Validate the requested retrieval count."""

        if not isinstance(top_k, int):
            raise RAGPipelineValidationError("top_k must be an integer.")
        if top_k <= 0:
            raise RAGPipelineValidationError(
            "top_k must be greater than 0."
        )

        if top_k > 20:
            raise RAGPipelineValidationError(
            "top_k cannot exceed 20."
        )
            raise RAGPipelineValidationError("top_k must be greater than 0.")

        return top_k

    @staticmethod
    def _build_sources(retrieved_chunks: list[dict[str, Any]]) -> list[RAGSource]:
        """Extract source metadata from retrieved chunks for the final response."""

        sources: list[RAGSource] = []
        for chunk in retrieved_chunks:
            sources.append(
                {
                    "chunk_id": str(chunk.get("chunk_id", "")),
                    "page_start": RAGPipeline._optional_int(chunk.get("page_start")),
                    "page_end": RAGPipeline._optional_int(chunk.get("page_end")),
                    "score": RAGPipeline._optional_float(chunk.get("score")),
                    "metadata": dict(chunk.get("metadata") or {}),
                }
            )

        return sources

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        """Convert optional numeric metadata into an integer."""

        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        """Convert optional score metadata into a float."""

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None
