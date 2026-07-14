import logging
import re
from time import perf_counter
from typing import Any, TypedDict

from backend.services.llm_service import LLMService, LLMServiceError
from backend.services.retrieval_service import RetrievalService, RetrievalServiceError
from backend.services.reranker_service import RerankerService
import backend.config as config


logger = logging.getLogger(__name__)

# Lightweight entity patterns reused from the knowledge graph service.
_ENTITY_PATTERNS: dict[str, list[str]] = {
    "Equipment": [
        r"\b(pump|compressor|valve|motor|gearbox|turbine|reactor|boiler|conveyor|generator|sensor|controller|actuator|vessel|pipeline|drill|engine)\b",
    ],
    "Safety": [
        r"\b(safety|hazard|risk|lockout|tagout|ppe|incident|accident|emergency)\b",
    ],
    "Maintenance": [
        r"\b(maintenance|inspection|lubrication|calibration|overhaul|repair|preventive|predictive)\b",
    ],
    "Standards": [
        r"\b(iso|iec|api|ansi|astm|osha|nfpa|ieee)\b",
    ],
    "Technologies": [
        r"\b(iot|ai|ml|predictive maintenance|condition monitoring|digital twin|scada|plc|robotics|automation)\b",
    ],
    "SOPs": [
        r"\b(sop|standard operating procedure|procedure|work instruction)\b",
    ],
}

_COMPILED_ENTITY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (entity_type, re.compile(pattern, re.IGNORECASE))
    for entity_type, patterns in _ENTITY_PATTERNS.items()
    for pattern in patterns
]


class RAGEntity(TypedDict):
    """An industrial entity extracted from retrieved context."""

    label: str
    type: str


class RAGSource(TypedDict):
    """Source metadata included in the final RAG response."""

    chunk_id: str
    text: str
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
    context_chunks: int
    sources: list[RAGSource]
    entities: list[RAGEntity]
    retrieval_scope: str
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

    def ask(self, question: str, top_k: int = 5, document_ids: list[str] | None = None) -> RAGResponse:
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
        started_at = perf_counter()

        try:
            # RetrievalService handles embeddings and vector search through its
            # own dependencies; the pipeline only coordinates the call.
            retrieval_started_at = perf_counter()
            
            is_reranker_enabled = getattr(config, "ENABLE_RERANKER", False)
            retrieval_top_k = getattr(config, "RERANK_TOP_N", 20) if is_reranker_enabled else clean_top_k
            
            retrieval = self.retrieval_service.retrieve(
                question=clean_question,
                top_k=max(clean_top_k, retrieval_top_k),
                document_ids=document_ids,
            )
            logger.info(
                "RAG retrieval completed: top_k=%s results=%s latency_ms=%s",
                retrieval_top_k,
                len(retrieval.get("results", [])),
                int((perf_counter() - retrieval_started_at) * 1000),
            )
        except RetrievalServiceError as exc:
            raise RAGPipelineRetrievalError("Failed to retrieve context for the question.") from exc

        retrieved_chunks = retrieval.get("results", [])
        
        if is_reranker_enabled and len(retrieved_chunks) > 0:
            reranker = RerankerService()
            final_top_k = getattr(config, "FINAL_TOP_K", clean_top_k)
            
            # Rerank and log top candidate scores
            top_candidates = reranker.rerank(
                question=retrieval["question"],
                chunks=retrieved_chunks,
                top_k=final_top_k,
            )
            
            cleaned_chunks = self._cleanup_context(top_candidates)
            
            logger.info(
                "Reranking completed: candidates=%d final=%d",
                len(retrieved_chunks),
                len(cleaned_chunks),
            )
            
            for chunk in cleaned_chunks:
                logger.debug(
                    "Selected Chunk - ID: %s, Reranker Score: %s, Final Score: %s",
                    chunk["chunk_id"],
                    chunk.get("metadata", {}).get("reranker_score"),
                    chunk.get("metadata", {}).get("final_score")
                )
                
            retrieved_chunks = cleaned_chunks
            retrieval["results"] = retrieved_chunks

        try:
            # LLMService receives the retrieved chunks and owns all prompt and
            # Gemini-specific answer generation behavior.
            generation_started_at = perf_counter()
            llm_response = self.llm_service.generate_answer(
                question=retrieval["question"],
                retrieved_chunks=retrieved_chunks,
            )
            logger.info(
                "RAG generation completed: context_chunks=%s latency_ms=%s",
                len(retrieved_chunks),
                int((perf_counter() - generation_started_at) * 1000),
            )
        except LLMServiceError as exc:
            raise RAGPipelineGenerationError("Failed to generate an answer from retrieved context.") from exc

        logger.info(
            "RAG request completed: top_k=%s total_latency_ms=%s",
            clean_top_k,
            int((perf_counter() - started_at) * 1000),
        )

        # Build retrieval scope description
        retrieval_scope = self._build_retrieval_scope(document_ids, retrieved_chunks)

        return {
            "question": retrieval["question"],
            "answer": str(llm_response["answer"]),
            "retrieval": retrieval,
            "model": str(llm_response["model"]),
            "context_chunks": len(retrieved_chunks),
            "sources": self._build_sources(retrieved_chunks),
            "entities": self._extract_entities(retrieved_chunks),
            "retrieval_scope": retrieval_scope,
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

        return top_k

    @staticmethod
    def _build_sources(retrieved_chunks: list[dict[str, Any]]) -> list[RAGSource]:
        """Extract source metadata from retrieved chunks for the final response."""

        sources: list[RAGSource] = []
        for chunk in retrieved_chunks:
            raw_text = str(chunk.get("text", "")).strip()
            sources.append(
                {
                    "chunk_id": str(chunk.get("chunk_id", "")),
                    "text": raw_text[:500] if raw_text else "",
                    "page_start": RAGPipeline._optional_int(chunk.get("page_start")),
                    "page_end": RAGPipeline._optional_int(chunk.get("page_end")),
                    "score": RAGPipeline._optional_float(chunk.get("score")),
                    "metadata": dict(chunk.get("metadata") or {}),
                }
            )

        return sources

    @staticmethod
    def _build_retrieval_scope(
        document_ids: list[str] | None,
        retrieved_chunks: list[dict[str, Any]],
    ) -> str:
        """Build a human-readable description of the retrieval scope."""
        
        if not document_ids:
            return "Entire Knowledge Base"
        
        if len(document_ids) == 1:
            # Try to get filename from retrieved chunks
            for chunk in retrieved_chunks:
                metadata = chunk.get("metadata", {})
                if metadata.get("document_id") == document_ids[0]:
                    filename = metadata.get("filename", "")
                    if filename:
                        # Get just the filename without path
                        return filename.split("/")[-1]
            # Fallback to document_id if no filename found
            return f"{document_ids[0]}.pdf"
        
        # Multiple documents selected
        return f"{len(document_ids)} Selected Documents"

    @staticmethod
    def _extract_entities(retrieved_chunks: list[dict[str, Any]]) -> list[RAGEntity]:
        """Extract unique industrial entities from retrieved chunk text."""

        seen: set[str] = set()
        entities: list[RAGEntity] = []
        combined_text = " ".join(
            str(chunk.get("text", "")) for chunk in retrieved_chunks
        )

        for entity_type, pattern in _COMPILED_ENTITY_PATTERNS:
            for match in pattern.finditer(combined_text):
                label = match.group(1).strip().title()
                key = f"{entity_type}:{label}"
                if key not in seen:
                    seen.add(key)
                    entities.append({"label": label, "type": entity_type})

        return entities[:20]

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

    @staticmethod
    def _cleanup_context(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate/overlapping chunks and merge consecutive ones."""
        if not chunks:
            return []
            
        seen = set()
        unique = []
        for c in chunks:
            if c["chunk_id"] not in seen:
                seen.add(c["chunk_id"])
                unique.append(c)
                
        cleaned = []
        for chunk in unique:
            text = chunk.get("text", "").strip()
            if not text:
                continue
                
            is_overlap = False
            for existing in cleaned:
                existing_text = existing.get("text", "")
                if text in existing_text or existing_text in text:
                    is_overlap = True
                    # Keep the larger one
                    if len(text) > len(existing_text):
                        existing["text"] = text
                        existing["chunk_id"] = chunk["chunk_id"]
                    break
            if not is_overlap:
                cleaned.append(chunk)
                
        return cleaned
