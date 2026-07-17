"""RAG pipeline orchestration for INDUS MIND.

Coordinates the entire retrieval and generation process.
This is the single authoritative answer path — all queries flow through
RAGPipeline.ask().
"""

import logging
import re
from time import perf_counter
from typing import Any, TypedDict

import backend.config as config
from backend.services.context_constructor import ContextConstructor
from backend.services.context_validator import ContextValidation, ContextValidator, ValidationVerdict
from backend.services.embedding_service import EmbeddingService
from backend.services.llm_service import LLMService, LLMServiceError
from backend.services.query_understanding import QueryUnderstandingEngine
from backend.services.reranker_service import RerankerService
from backend.services.response_validator import ResponseValidator
from backend.services.retrieval_service import RetrievalService, RetrievalServiceError
from backend.services.semantic_cache_service import SemanticCacheService

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
    output_format: str
    success: bool
    rejection_reason: str | None
    missing_entities: list[str] | None


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

    Pipeline:
    Query → Understand → Retrieve → Rerank → Construct → Validate → LLM → Confidence
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_service: LLMService,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.semantic_cache = SemanticCacheService(embedding_service) if embedding_service else None
        
        # New Architecture Services
        self.query_understanding = QueryUnderstandingEngine()
        self.context_constructor = ContextConstructor(vectordb_service=retrieval_service.vectordb_service)
        self.context_validator = ContextValidator()
        self.response_validator = ResponseValidator()

    def ask(self, question: str, top_k: int = 5, document_ids: list[str] | None = None, user_role: str = "public") -> RAGResponse:
        """Answer a user question using retrieved document context."""

        clean_question = self._validate_question(question)
        clean_top_k = self._validate_top_k(top_k)
        started_at = perf_counter()

        logger.info(
            "RAG Pipeline: request accepted. query='%s', document_ids=%s",
            clean_question,
            document_ids,
        )

        # ── Stage 0: Check Semantic Cache ────────────────────────────
        if self.semantic_cache:
            if document_ids:
                print("\n[RAG DEBUG] ====================================================")
                print("[RAG DEBUG] Semantic Cache: BYPASSED (document_ids provided)")
                print("[RAG DEBUG] ====================================================\n")
            else:
                # We pass document_ids to the cache so it respects scoping
                cached_response = self.semantic_cache.get(clean_question, document_ids)
                if cached_response:
                    print("\n[RAG DEBUG] ====================================================")
                    print("[RAG DEBUG] Semantic Cache: HIT")
                    print("[RAG DEBUG] Searching: N/A")
                    print("[RAG DEBUG] Retrieved Chunks: 0")
                    print("[RAG DEBUG] ====================================================\n")
                    cached_response["retrieval_time_ms"] = int((perf_counter() - started_at) * 1000)
                    return cached_response
                else:
                    print("\n[RAG DEBUG] ====================================================")
                    print("[RAG DEBUG] Semantic Cache: MISS")
                    print("[RAG DEBUG] ====================================================\n")

        # ── Stage 1: Query Understanding ─────────────────────────────
        query_plan = self.query_understanding.analyze(clean_question, document_ids)
        dynamic_top_k = max(clean_top_k, getattr(query_plan, "num_retrievals", clean_top_k))

        # ── Stage 2 & 3: Retrieval and Reranking ─────────────────────
        try:
            retrieval_started_at = perf_counter()
            retrieved_chunks = []
            
            enable_reranker = getattr(config, "ENABLE_RERANKER", True)
            reranker = RerankerService() if enable_reranker else None
            final_top_k = max(getattr(config, "FINAL_TOP_K", dynamic_top_k), dynamic_top_k + 3)

            if query_plan.is_multi_query and len(query_plan.search_queries) > 1:
                logger.info("Executing multi-query independent retrieval for %d queries.", len(query_plan.search_queries))
                
                query_results = []
                per_query_k = max(3, final_top_k // len(query_plan.search_queries))
                
                for sq in query_plan.search_queries:
                    # 1. Retrieve independently
                    cands = self.retrieval_service.execute_query(sq, query_plan.intent, query_plan.document_selection, user_role)
                    
                    # 2. Rerank independently against the specific sub-query
                    if reranker and cands:
                        cands = reranker.rerank(sq.text, cands, top_k=per_query_k, query_plan=query_plan)
                        
                    if cands:
                        query_results.append(cands)
                
                # 3. Interleave independently retrieved and reranked results
                if query_results:
                    iters = [iter(g) for g in query_results]
                    while iters and len(retrieved_chunks) < final_top_k:
                        for it in list(iters):
                            if len(retrieved_chunks) >= final_top_k:
                                break
                            try:
                                retrieved_chunks.append(next(it))
                            except StopIteration:
                                iters.remove(it)
            else:
                # Standard single-pass retrieval and rerank
                retrieved_chunks = self.retrieval_service.execute(query_plan, user_role)
                if reranker and retrieved_chunks:
                    retrieved_chunks = reranker.rerank(
                        question=clean_question,
                        chunks=retrieved_chunks,
                        top_k=final_top_k,
                        query_plan=query_plan
                    )

            logger.info(
                "Retrieval & Reranking completed: strategy=%s final_chunks=%s latency_ms=%s",
                query_plan.retrieval_strategy.value,
                len(retrieved_chunks),
                int((perf_counter() - retrieval_started_at) * 1000),
            )
        except RetrievalServiceError as exc:
            raise RAGPipelineRetrievalError("Failed to retrieve context for the question.") from exc

        # ── Stage 4: Context Construction ────────────────────────────
        max_tokens = getattr(config, "MAX_CONTEXT_TOKENS", 6000)
        constructed_context = self.context_constructor.construct(
            chunks=retrieved_chunks,
            query_plan=query_plan,
            max_tokens=max_tokens
        )
        
        doc_ids = list(set([c.get("metadata", {}).get("document_id") for c in constructed_context if c.get("metadata", {}).get("document_id")]))
        chunk_ids = [c.get("chunk_id") for c in constructed_context]
        pages = list(set([c.get("metadata", {}).get("page_start") for c in constructed_context if c.get("metadata", {}).get("page_start")]))
        chars = sum([len(c.get("text", "")) for c in constructed_context])
        
        print("\n[RAG DEBUG] ====================================================")
        print("[RAG DEBUG] STEP 8 - Final Context")
        print(f"[RAG DEBUG] Chunks selected for Gemini: {len(constructed_context)}")
        print(f"[RAG DEBUG] Document IDs: {doc_ids}")
        print(f"[RAG DEBUG] Chunk IDs: {chunk_ids}")
        print(f"[RAG DEBUG] Pages: {pages}")
        print(f"[RAG DEBUG] Characters: {chars}")
        print(f"[RAG DEBUG] Total Tokens: {chars // 4}")
        print("[RAG DEBUG] ====================================================\n")

        logger.info("Context construction yielded %d formatted chunks.", len(constructed_context))

        # ── Stage 5: Context Validation ──────────────────────────────
        validation = self.context_validator.validate(query_plan, constructed_context)
        
        if validation.verdict == ValidationVerdict.FAIL:
            logger.warning("Retrieval REJECTED: %s", validation.reason)
            return self._build_rejection_response(clean_question, started_at, validation)
            
        if validation.verdict == ValidationVerdict.PARTIAL:
            logger.warning("Retrieval PARTIAL: %s. Proceeding to LLM with warning.", validation.reason)
            # Add warning to the first chunk
            if constructed_context:
                missing = ", ".join(validation.missing_entities)
                warning = f"[SYSTEM WARNING: The retrieved context does NOT contain information about {missing}. Acknowledge this limitation in your response.]\n\n"
                constructed_context[0]["text"] = warning + constructed_context[0]["text"]

        # ── Stage 6: Generate answer with Self-Correction ────────────
        try:
            generation_started_at = perf_counter()
            max_retries = 1
            attempts = 0
            correction_instruction = None
            llm_response = None
            
            while attempts <= max_retries:
                attempts += 1
                
                print("\n[RAG DEBUG] ====================================================")
                print("[RAG DEBUG] STEP 9 - Gemini Request")
                print(f"[RAG DEBUG] Prompt Length: {len(clean_question)}")
                print(f"[RAG DEBUG] Context Length: {chars}")
                print(f"[RAG DEBUG] Documents Used: {len(doc_ids)}")
                print("[RAG DEBUG] ====================================================\n")
                
                llm_response = self.llm_service.generate_answer(
                    question=clean_question,
                    retrieved_chunks=constructed_context,
                    intent=query_plan.intent.value,
                    output_format=query_plan.output_format,
                    correction_instruction=correction_instruction
                )
                
                answer_text = str(llm_response.get("answer", ""))
                
                # ── Response Validation ──
                val_result = self.response_validator.validate(answer_text, query_plan, constructed_context)
                
                if val_result.is_valid:
                    logger.info("Response Validation PASSED on attempt %d.", attempts)
                    break
                    
                logger.warning(
                    "Response Validation FAILED on attempt %d. Reason: %s", 
                    attempts, val_result.reason
                )
                
                if attempts <= max_retries:
                    correction_instruction = val_result.reason
                else:
                    logger.error("Response Validation max retries reached. Returning best effort answer.")
            
            logger.info(
                "RAG generation completed: attempts=%d latency_ms=%s",
                attempts,
                int((perf_counter() - generation_started_at) * 1000),
            )
        except LLMServiceError as exc:
            raise RAGPipelineGenerationError("Failed to generate an answer from retrieved context.") from exc

        # ── Stage 7: Compute grounded confidence ─────────────────────
        confidence = self._compute_confidence(
            question=clean_question,
            answer=str(llm_response.get("answer", "")),
            chunks=constructed_context,
            validation=validation,
        )

        logger.info(
            "RAG request completed: confidence=%d total_latency_ms=%s",
            confidence,
            int((perf_counter() - started_at) * 1000),
        )

        final_response = {
            "question": clean_question,
            "answer": str(llm_response["answer"]),
            "retrieval": {"results": constructed_context, "intent": query_plan.intent.value},
            "model": str(llm_response["model"]),
            "context_chunks": len(constructed_context),
            "sources": self._build_sources(constructed_context),
            "entities": self._extract_entities(constructed_context),
            "retrieval_scope": self._build_retrieval_scope(query_plan.document_selection.selected_ids, constructed_context),
            "confidence": confidence,
            "intent": query_plan.intent.value,
            "output_format": query_plan.output_format,
            "success": True,
            "rejection_reason": None,
            "missing_entities": validation.missing_entities,
        }

        print("\n[RAG DEBUG] ====================================================")
        print("[RAG DEBUG] STEP 10 - Final Response")
        print(f"[RAG DEBUG] Grounded = {confidence > 50}")
        print(f"[RAG DEBUG] Citations Used: {len(final_response['sources'])}")
        print(f"[RAG DEBUG] Documents Referenced: {len(set([s.get('metadata', {}).get('document_id') for s in final_response['sources']]))}")
        print("[RAG DEBUG] ====================================================\n")

        if self.semantic_cache:
            self.semantic_cache.set(clean_question, document_ids, final_response)

        return final_response

    def _build_rejection_response(
        self, question: str, started_at: float, validation: ContextValidation
    ) -> RAGResponse:
        """Return structured rejection with diagnostic info."""
        
        if validation.missing_entities:
            entities = ", ".join(validation.missing_entities)
            answer = f"I couldn't find sufficient information about {entities} in the selected documents. Try selecting more documents or rephrasing your question."
        else:
            answer = "I do not have sufficient evidence in the selected documents to answer this question accurately."
            
        return {
            "question": question,
            "answer": answer,
            "retrieval": {"results": [], "intent": "unknown"},
            "model": "system-rejection",
            "context_chunks": 0,
            "sources": [],
            "entities": [],
            "retrieval_scope": "N/A",
            "confidence": 0,
            "intent": "unknown",
            "success": False,
            "rejection_reason": validation.reason,
            "missing_entities": validation.missing_entities,
        }

    # ── Confidence Scoring ───────────────────────────────────────────

    @staticmethod
    def _compute_confidence(
        question: str,
        answer: str,
        chunks: list[dict[str, Any]],
        validation: ContextValidation,
    ) -> int:
        """Compute a grounded confidence score (0-100)."""

        if not chunks or not answer:
            return 15

        # Best cross-encoder score normalized (0-1)
        best_score = max(validation.relevance_scores) if validation.relevance_scores else 0.0
        score_component = max(0.0, min(1.0, (best_score + 5) / 15))

        # Entity coverage component
        entity_coverage = 1.0
        if validation.entity_coverage:
            covered = sum(1 for v in validation.entity_coverage.values() if v)
            entity_coverage = covered / len(validation.entity_coverage)

        # Source diversity
        doc_ids = set()
        for chunk in chunks:
            doc_id = (chunk.get("metadata") or {}).get("document_id", "")
            if doc_id:
                doc_ids.add(doc_id)
        diversity = min(1.0, len(doc_ids) / max(1, len(chunks)))

        # Answer-context overlap
        answer_terms = set(re.findall(r"[a-z0-9]+", answer.lower()))
        context_terms = set()
        for chunk in chunks:
            context_terms.update(re.findall(r"[a-z0-9]+", str(chunk.get("text", "")).lower()))
        
        overlap = len(answer_terms & context_terms) / len(answer_terms) if answer_terms else 0.0
        
        # Chunk count adequacy
        chunk_adequacy = min(1.0, len(chunks) / 3)

        # Weighted combination
        confidence = (
            0.35 * score_component
            + 0.25 * entity_coverage
            + 0.20 * overlap
            + 0.10 * diversity
            + 0.10 * chunk_adequacy
        )

        # Penalties
        if validation.missing_entities:
            confidence *= 0.6
        if best_score < -2.0:
            confidence *= 0.5
            
        fallback_phrases = [
            "couldn't find",
            "not enough",
            "insufficient evidence",
            "no supporting",
        ]
        if any(p in answer.lower() for p in fallback_phrases):
            confidence = min(confidence, 0.25)

        return int(round(min(100.0, max(0.0, confidence * 100))))

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
