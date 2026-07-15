"""RAG pipeline orchestration for INDUS MIND.

Coordinates retrieval, reranking, MMR diversification, context cleanup,
and answer generation.  This is the single authoritative answer path —
all queries flow through RAGPipeline.ask().
"""

import logging
import re
from time import perf_counter
from typing import Any, TypedDict

import numpy as np

from backend.services.llm_service import LLMService, LLMServiceError
from backend.services.retrieval_service import RetrievalService, RetrievalServiceError
from backend.services.reranker_service import RerankerService
from backend.services.embedding_service import EmbeddingService
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
    confidence: int
    intent: str
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

    Single authoritative answer path:
    Query → Retrieval → Reranking → MMR → Context Cleanup → Generation → Confidence

    The pipeline coordinates existing services only. It does not generate
    embeddings directly, access ChromaDB, parse PDFs, or call Gemini directly.
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service
        # Embedding service needed for MMR similarity computation
        self.embedding_service = embedding_service

    def ask(self, question: str, top_k: int = 5, document_ids: list[str] | None = None) -> RAGResponse:
        """Answer a user question using retrieved document context.

        Pipeline stages:
        1. Validate input
        2. Retrieve candidates (hybrid RRF with BM25 + dense + structured)
        3. Rerank with cross-encoder (if enabled)
        4. Diversify with MMR (if enabled)
        5. Cleanup and deduplicate context
        6. Generate answer with Gemini
        7. Compute grounded confidence score
        """

        clean_question = self._validate_question(question)
        clean_top_k = self._validate_top_k(top_k)
        started_at = perf_counter()

        # ── Stage 1: Retrieve candidates ─────────────────────────────
        try:
            retrieval_started_at = perf_counter()

            is_reranker_enabled = getattr(config, "ENABLE_RERANKER", True)
            retrieval_top_k = getattr(config, "RERANK_TOP_N", 30) if is_reranker_enabled else clean_top_k

            retrieval = self.retrieval_service.retrieve(
                question=clean_question,
                top_k=max(clean_top_k, retrieval_top_k),
                document_ids=document_ids,
            )
            logger.info(
                "RAG retrieval completed: top_k=%s results=%s intent=%s latency_ms=%s",
                retrieval_top_k,
                len(retrieval.get("results", [])),
                retrieval.get("intent", "unknown"),
                int((perf_counter() - retrieval_started_at) * 1000),
            )
        except RetrievalServiceError as exc:
            raise RAGPipelineRetrievalError("Failed to retrieve context for the question.") from exc

        retrieved_chunks = retrieval.get("results", [])
        intent = retrieval.get("intent", "factoid")

        # ── Stage 2: Cross-encoder reranking ─────────────────────────
        if is_reranker_enabled and len(retrieved_chunks) > 0:
            reranker = RerankerService()
            final_top_k = getattr(config, "FINAL_TOP_K", clean_top_k)

            top_candidates = reranker.rerank(
                question=retrieval["question"],
                chunks=retrieved_chunks,
                top_k=max(final_top_k, clean_top_k + 3),  # Over-retrieve slightly for MMR
            )

            logger.info(
                "Reranking completed: candidates=%d final=%d",
                len(retrieved_chunks),
                len(top_candidates),
            )
            retrieved_chunks = top_candidates

        # ── Stage 3: MMR Diversification ─────────────────────────────
        if getattr(config, "ENABLE_MMR", True) and len(retrieved_chunks) > clean_top_k:
            mmr_lambda = getattr(config, "MMR_LAMBDA", 0.7)
            retrieved_chunks = self._apply_mmr(
                retrieved_chunks,
                lambda_param=mmr_lambda,
                top_k=clean_top_k,
            )
            logger.info("MMR diversification: selected %d chunks", len(retrieved_chunks))

        # ── Stage 4: Context cleanup ─────────────────────────────────
        cleaned_chunks = self._cleanup_context(retrieved_chunks)
        retrieval["results"] = cleaned_chunks

        # ── Stage 5: Generate answer ─────────────────────────────────
        try:
            generation_started_at = perf_counter()
            llm_response = self.llm_service.generate_answer(
                question=retrieval["question"],
                retrieved_chunks=cleaned_chunks,
            )
            logger.info(
                "RAG generation completed: context_chunks=%s latency_ms=%s",
                len(cleaned_chunks),
                int((perf_counter() - generation_started_at) * 1000),
            )
        except LLMServiceError as exc:
            raise RAGPipelineGenerationError("Failed to generate an answer from retrieved context.") from exc

        # ── Stage 6: Compute grounded confidence ─────────────────────
        confidence = self._compute_confidence(
            question=clean_question,
            answer=str(llm_response.get("answer", "")),
            chunks=cleaned_chunks,
            intent=intent,
        )

        logger.info(
            "RAG request completed: top_k=%s confidence=%d total_latency_ms=%s",
            clean_top_k,
            confidence,
            int((perf_counter() - started_at) * 1000),
        )

        retrieval_scope = self._build_retrieval_scope(document_ids, cleaned_chunks)

        return {
            "question": retrieval["question"],
            "answer": str(llm_response["answer"]),
            "retrieval": retrieval,
            "model": str(llm_response["model"]),
            "context_chunks": len(cleaned_chunks),
            "sources": self._build_sources(cleaned_chunks),
            "entities": self._extract_entities(cleaned_chunks),
            "retrieval_scope": retrieval_scope,
            "confidence": confidence,
            "intent": intent,
            "success": True,
        }

    # ── MMR Diversification ──────────────────────────────────────────

    def _apply_mmr(
        self,
        chunks: list[dict[str, Any]],
        lambda_param: float = 0.7,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Apply Maximal Marginal Relevance to diversify the result set.

        MMR_score(chunk) = λ * relevance(chunk) - (1-λ) * max_sim(chunk, selected)

        Uses text-based similarity as a fallback when embeddings are unavailable.
        """

        if len(chunks) <= top_k:
            return chunks

        # Compute chunk-chunk similarity matrix using text overlap
        # (cheaper than re-embedding all chunks)
        n = len(chunks)
        similarity_matrix = self._compute_text_similarity_matrix(chunks)

        # Normalize relevance scores to [0, 1]
        scores = [float(c.get("score", 0.0) or 0.0) for c in chunks]
        max_score = max(scores) if scores else 1.0
        if max_score > 0:
            norm_scores = [s / max_score for s in scores]
        else:
            norm_scores = [0.0] * n

        # Greedy MMR selection
        selected_indices: list[int] = []
        remaining = set(range(n))

        for _ in range(min(top_k, n)):
            best_idx = -1
            best_mmr = float("-inf")

            for idx in remaining:
                relevance = norm_scores[idx]

                if selected_indices:
                    max_sim = max(
                        similarity_matrix[idx][sel_idx]
                        for sel_idx in selected_indices
                    )
                else:
                    max_sim = 0.0

                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim

                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = idx

            if best_idx >= 0:
                selected_indices.append(best_idx)
                remaining.discard(best_idx)

        return [chunks[i] for i in selected_indices]

    @staticmethod
    def _compute_text_similarity_matrix(chunks: list[dict[str, Any]]) -> list[list[float]]:
        """Compute pairwise text similarity using token Jaccard overlap."""

        tokenized = []
        for chunk in chunks:
            text = str(chunk.get("text", "")).lower()
            tokens = set(re.findall(r"[a-z0-9]+", text))
            tokenized.append(tokens)

        n = len(chunks)
        matrix = [[0.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                if tokenized[i] and tokenized[j]:
                    intersection = len(tokenized[i] & tokenized[j])
                    union = len(tokenized[i] | tokenized[j])
                    sim = intersection / union if union > 0 else 0.0
                else:
                    sim = 0.0
                matrix[i][j] = sim
                matrix[j][i] = sim

        return matrix

    # ── Confidence Scoring ───────────────────────────────────────────

    @staticmethod
    def _compute_confidence(
        question: str,
        answer: str,
        chunks: list[dict[str, Any]],
        intent: str,
    ) -> int:
        """Compute a grounded confidence score (0-100).

        Based on:
        - Reranker score distribution (if available)
        - Source diversity (unique documents)
        - Answer-context overlap (does the answer use the context?)
        - Retrieval signal strength
        """

        if not chunks or not answer:
            return 15

        # Factor 1: Best retrieval score (reranker or RRF)
        scores = []
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            reranker_score = meta.get("reranker_score")
            if reranker_score is not None:
                scores.append(float(reranker_score))
            else:
                scores.append(float(chunk.get("score", 0.0) or 0.0))

        if scores:
            best_score = max(scores)
            # Cross-encoder scores typically range from -10 to +10
            # Normalize to 0-1
            score_component = max(0.0, min(1.0, (best_score + 5) / 15))
        else:
            score_component = 0.0

        # Factor 2: Source diversity
        doc_ids = set()
        for chunk in chunks:
            doc_id = (chunk.get("metadata") or {}).get("document_id", "")
            if doc_id:
                doc_ids.add(doc_id)
        diversity = min(1.0, len(doc_ids) / max(1, len(chunks)))

        # Factor 3: Answer-context overlap
        answer_terms = set(re.findall(r"[a-z0-9]+", answer.lower()))
        context_terms = set()
        for chunk in chunks:
            context_terms.update(re.findall(r"[a-z0-9]+", str(chunk.get("text", "")).lower()))
        if answer_terms:
            overlap = len(answer_terms & context_terms) / len(answer_terms)
        else:
            overlap = 0.0

        # Factor 4: Chunk count adequacy
        chunk_adequacy = min(1.0, len(chunks) / 3)

        # Weighted combination
        confidence = (
            0.40 * score_component
            + 0.15 * diversity
            + 0.30 * overlap
            + 0.15 * chunk_adequacy
        )

        # Boost for navigational queries with structured matches
        if intent == "navigational":
            has_structured = any(
                (c.get("metadata") or {}).get("structured_score", 0) > 0.5
                for c in chunks
            )
            if has_structured:
                confidence = min(1.0, confidence + 0.15)

        # Detect fallback answers
        fallback_phrases = [
            "couldn't find",
            "not enough",
            "insufficient evidence",
            "no supporting",
        ]
        if any(p in answer.lower() for p in fallback_phrases):
            confidence = min(confidence, 0.25)

        return int(round(min(100.0, max(0.0, confidence * 100))))

    # ── Context Cleanup ──────────────────────────────────────────────

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

    # ── Source & Entity Building ──────────────────────────────────────

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
            for chunk in retrieved_chunks:
                metadata = chunk.get("metadata", {})
                if metadata.get("document_id") == document_ids[0]:
                    filename = metadata.get("filename", "")
                    if filename:
                        return filename.split("/")[-1]
            return f"{document_ids[0]}.pdf"

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

    # ── Validation ───────────────────────────────────────────────────

    @staticmethod
    def _validate_question(question: str) -> str:
        if not isinstance(question, str):
            raise RAGPipelineValidationError("question must be a string.")
        clean_question = question.strip()
        if not clean_question:
            raise RAGPipelineValidationError("question cannot be empty.")
        return clean_question

    @staticmethod
    def _validate_top_k(top_k: int) -> int:
        if not isinstance(top_k, int):
            raise RAGPipelineValidationError("top_k must be an integer.")
        if top_k <= 0:
            raise RAGPipelineValidationError("top_k must be greater than 0.")
        if top_k > 20:
            raise RAGPipelineValidationError("top_k cannot exceed 20.")
        return top_k

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
