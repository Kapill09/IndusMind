"""Production-grade hybrid retrieval for INDUS MIND.

Combines three independent retrieval channels — dense vector search, BM25
sparse retrieval, and structured metadata matching — and fuses them using
Reciprocal Rank Fusion (RRF).  Source filtering is enforced as a hard
invariant via the ScopeEnforcer.
"""

from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from transformers.models.chameleon import image_processing_chameleon_fast
from backend.services import query_analyzer
import logging
import re
from typing import Any, Iterable, TypedDict

from backend.services.bm25_service import BM25Service
from backend.services.document_id_validation import sanitize_document_ids
from backend.services.embedding_service import EmbeddingService, EmbeddingServiceError
from backend.services.query_analyzer import (
    AnalyzedQuery,
    QueryAnalyzer,
    QueryIntent,
    StructuredQuery,
)
from backend.services.scope_enforcer import ScopeEnforcer
from backend.services.vectordb_service import (
    VectorDBService,
    VectorDBServiceError,
    VectorSearchResult,
)
import backend.config as config

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────
RRF_K = getattr(config, "RRF_K", 60)
MAX_SEMANTIC_CANDIDATES = getattr(config, "MAX_SEMANTIC_CANDIDATES", 50)
BM25_TOP_K = getattr(config, "BM25_TOP_K", 50)

STRUCTURED_METADATA_FIELDS = {
    "problem_statement": "problem_statement_number",
    "section": "section_number",
    "chapter": "chapter_number",
    "figure": "figure_number",
    "table": "table_number",
}


class RetrievalResult(TypedDict):
    """One hybrid retrieval result returned to API callers."""

    chunk_id: str
    text: str
    page_start: int | None
    page_end: int | None
    metadata: dict[str, Any]
    distance: float | None
    score: float


class RetrievalResponse(TypedDict):
    """Structured response returned for a retrieval request."""

    question: str
    results: list[RetrievalResult]
    intent: str


class RetrievalServiceError(Exception):
    """Base exception for all retrieval service errors."""


class RetrievalValidationError(RetrievalServiceError):
    """Raised when the retrieval request is invalid."""


class RetrievalEmbeddingError(RetrievalServiceError):
    """Raised when the question embedding cannot be generated."""


class RetrievalSearchError(RetrievalServiceError):
    """Raised when hybrid retrieval cannot be completed."""


class RetrievalService:
    """Retrieve relevant INDUS MIND document chunks with production-grade hybrid ranking.

    Three-channel retrieval with Reciprocal Rank Fusion:
    - Channel A: Dense vector search (embedding similarity)
    - Channel B: BM25 sparse retrieval (lexical matching with IDF)
    - Channel C: Structured metadata matching (exact navigation lookups)

    Source filtering is enforced as a hard invariant at every stage.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vectordb_service: VectorDBService,
        bm25_service: BM25Service | None = None,
        query_analyzer: QueryAnalyzer | None = None,
    ) -> None:
        self.embedding_service = embedding_service
        self.vectordb_service = vectordb_service
        self.bm25_service = bm25_service or BM25Service()
        self.query_analyzer = query_analyzer or QueryAnalyzer()

    def retrieve(
    self,
    question: str,
    top_k: int = 8,
    document_ids: list[str] | None = None,
    ) -> RetrievalResponse:
        """Retrieve the top K chunks using three-channel hybrid retrieval with RRF."""

        logger.info("=" * 80)
        logger.info("RETRIEVAL SERVICE")
        logger.info("Question: %s", question)
        logger.info("Received document_ids: %s", document_ids)
        logger.info("=" * 80)

        clean_question = self._validate_question(question)
        clean_top_k = self._validate_top_k(top_k)
        clean_document_ids = sanitize_document_ids(document_ids)

        # ── Stage 1: Query Analysis ──────────────────────────────────
        analyzed = self.query_analyzer.full_analyze(clean_question)
        logger.info(
            "Query analyzed: intent=%s structured=%s sub_queries=%d hyde=%s",
            analyzed.intent.value,
            analyzed.structured is not None,
            len(analyzed.sub_queries),
            analyzed.hyde_passage is not None,
        )

        # ── Stage 2: Setup scope enforcer ────────────────────────────
        scope = ScopeEnforcer(clean_document_ids)

        # ── Stage 3: Structured fast-path for navigational queries ───
        if analyzed.structured:
            fast_results = self._structured_fast_path(
                analyzed.structured, clean_document_ids, clean_top_k
            )
            if fast_results:
                safe_results = scope.enforce(fast_results)
                logger.info(
                    "Structured fast-path returned %d results (post-scope: %d)",
                    len(fast_results), len(safe_results),
                )
                return {
                    "question": clean_question,
                    "results": safe_results,
                    "intent": analyzed.intent.value,
                }

        # ── Stage 4: Multi-query or single-query retrieval ───────────
        if analyzed.is_multi_query:
            all_results = self._multi_query_retrieve(
                analyzed, clean_document_ids, clean_top_k, scope
            )
        else:
            all_results = self._single_query_retrieve(
                analyzed, clean_document_ids, clean_top_k, scope
            )

        # ── Final scope enforcement ──────────────────────────────────
        safe_results = scope.enforce(all_results)

        logger.info(
            "Retrieval completed: intent=%s results=%d scope=%s",
            analyzed.intent.value,
            len(safe_results),
            "scoped" if scope.is_scoped else "global",
        )

        return {
            "question": clean_question,
            "results": safe_results[:clean_top_k],
            "intent": analyzed.intent.value,
        }

    def _single_query_retrieve(
        self,
        analyzed: AnalyzedQuery,
        document_ids: list[str] | None,
        top_k: int,
        scope: ScopeEnforcer,
    ) -> list[RetrievalResult]:
        """Run three-channel retrieval for a single query and fuse with RRF."""

        query = analyzed.original_query

        # ── Channel A: Dense vector search ───────────────────────────
        embed_text = analyzed.hyde_passage or query
        try:
            question_embedding = self.embedding_service.generate_embedding(
                embed_text, is_query=True
            )
        except EmbeddingServiceError as exc:
            raise RetrievalEmbeddingError("Failed to generate question embedding.") from exc

        where = {"document_id": {"$in": document_ids}} if document_ids else None
        try:
            dense_results = self.vectordb_service.search(
                query_embedding=question_embedding,
                top_k=MAX_SEMANTIC_CANDIDATES,
                where=where,
            )
        except VectorDBServiceError as exc:
            raise RetrievalSearchError("Failed to retrieve semantic candidates.") from exc

        dense_ranked = [
            {
                "chunk_id": r["chunk_id"],
                "text": r["text"],
                "metadata": r.get("metadata", {}),
                "distance": r.get("distance"),
            }
            for r in dense_results
        ]

        logger.info("=" * 80)
        logger.info("VECTOR SEARCH RESULTS")
        logger.info("Retrieved %d chunks", len(dense_ranked))

        for i, chunk in enumerate(dense_ranked[:10], 1):
            logger.info(
                "%d | %.4f | %s",
                i,
                chunk.get("distance", 0) if chunk.get("distance") is not None else 0,
                chunk.get("text", "")[:150].replace("\n", " ")
            )

        # ── Channel B: BM25 sparse retrieval ─────────────────────────
        bm25_ranked: list[dict[str, Any]] = []

        logger.info(
            "BM25 Index Size = %d",
            self.bm25_service.index_size if self.bm25_service else -1   ,
        )

        if self.bm25_service and self.bm25_service.index_size > 0:
            bm25_results = self.bm25_service.search(
                query=query,
        top_k=BM25_TOP_K,
                document_ids=document_ids,
            )

            logger.info("=" * 60)
            logger.info("BM25 RESULTS")
            logger.info(bm25_results[:5])

            bm25_ranked = [
                {
                    "chunk_id": r["chunk_id"],
                    "text": r["text"],
            "metadata": r.get("metadata", {}),
            "distance": None,
            "bm25_score": r["score"],
        }
        for r in bm25_results
    ]

            logger.info("=" * 80)
            logger.info("BM25 RESULTS")

            for i, chunk in enumerate(bm25_ranked[:10], 1):
                logger.info(
                    "%d | %.4f | %s",
                    i,
                    chunk.get("bm25_score", 0),
                    chunk.get("text", "")[:150].replace("\n", " ")
                )

        # ── Channel C: Structured metadata matching ──────────────────
        structured_ranked: list[dict[str, Any]] = []
        if analyzed.structured:
            structured_ranked = self._structured_metadata_search(
                analyzed.structured, document_ids
            )

        # ── Reciprocal Rank Fusion ───────────────────────────────────
        fused = self._reciprocal_rank_fusion(
            [dense_ranked, bm25_ranked, structured_ranked],
            top_k=max(top_k * 3, 30),  # Over-retrieve for reranker
        )
        for c in fused[:10]:
            logger.info(
                "%s | %.4f | %s",
                c["metadata"].get("filename"),
                c.get("rrf_score"),
                c["text"][:100]
            )

        logger.info("=" * 80)
        logger.info("HYBRID RESULTS")

        for i, chunk in enumerate(fused[:10], 1):
            logger.info(
                "%d | %.4f | %s",
                i,
                chunk.get("rrf_score", 0),
                chunk.get("text", "")[:150].replace("\n", " ")
            )

        # ── Format results ───────────────────────────────────────────
        return self._format_fused_results(fused, analyzed)

    def _multi_query_retrieve(
        self,
        analyzed: AnalyzedQuery,
        document_ids: list[str] | None,
        top_k: int,
        scope: ScopeEnforcer,
    ) -> list[RetrievalResult]:
        """Run independent retrieval for each sub-query and balance results.

        For comparison queries like "Compare D2DAP with IDS", each sub-query
        gets an equal share of the final top-K to ensure balanced representation.
        """

        sub_queries = analyzed.search_queries
        per_query_k = max(3, top_k // len(sub_queries))
        all_results: list[RetrievalResult] = []
        seen_chunk_ids: set[str] = set()

        for sub_query in sub_queries:
            # Create a simple AnalyzedQuery for the sub-query
            sub_analyzed = AnalyzedQuery(
                original_query=sub_query,
                intent=QueryIntent.FACTOID,
            )

            sub_results = self._single_query_retrieve(
                sub_analyzed, document_ids, per_query_k * 3, scope
            )

            # Apply scope enforcement on sub-results
            safe_sub = scope.enforce(sub_results)

            # Add unique results up to per-query quota
            added = 0
            for result in safe_sub:
                if added >= per_query_k:
                    break
                if result["chunk_id"] not in seen_chunk_ids:
                    seen_chunk_ids.add(result["chunk_id"])
                    all_results.append(result)
                    added += 1

        logger.info(
            "Multi-query retrieval: sub_queries=%d total_results=%d",
            len(sub_queries), len(all_results),
        )

        return all_results

    def _structured_fast_path(
        self,
        structured_query: StructuredQuery,
        document_ids: list[str] | None,
        top_k: int,
    ) -> list[RetrievalResult]:
        """Fetch exact metadata matches directly from the vector database."""

        where_conditions = []
        identifier = self._normalize_identifier(structured_query.identifier)
        metadata_field = STRUCTURED_METADATA_FIELDS.get(structured_query.query_type)

        if structured_query.query_type == "page":
            page_num = self._metadata_int(structured_query.identifier)
            if page_num is not None:
                where_conditions.append({"page_start": page_num})
        elif metadata_field and identifier:
            where_conditions.append({metadata_field: identifier})

        if not where_conditions:
            return []

        if document_ids:
            where_conditions.append({"document_id": {"$in": document_ids}})

        where = (
            where_conditions[0]
            if len(where_conditions) == 1
            else {"$and": where_conditions}
        )

        try:
            results = self.vectordb_service.get_chunks(limit=100, where=where)
        except Exception:
            return []

        formatted: list[RetrievalResult] = []
        for chunk in results[:top_k]:
            metadata = dict(chunk.get("metadata") or {})
            metadata["retrieval_mode"] = "structured_fast_path"
            metadata["structured_score"] = 1.0
            formatted.append({
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "page_start": self._metadata_int(metadata.get("page_start")),
                "page_end": self._metadata_int(metadata.get("page_end")),
                "metadata": metadata,
                "distance": None,
                "score": 1.0,
            })

        return formatted

    def _structured_metadata_search(
        self,
        structured_query: StructuredQuery,
        document_ids: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Search for chunks matching structured metadata fields."""

        where_conditions = []
        identifier = self._normalize_identifier(structured_query.identifier)
        metadata_field = STRUCTURED_METADATA_FIELDS.get(structured_query.query_type)

        if structured_query.query_type == "page":
            page_num = self._metadata_int(structured_query.identifier)
            if page_num is not None:
                where_conditions.append({"page_start": page_num})
        elif metadata_field and identifier:
            where_conditions.append({metadata_field: identifier})

        if not where_conditions:
            return []

        if document_ids:
            where_conditions.append({"document_id": {"$in": document_ids}})

        where = (
            where_conditions[0]
            if len(where_conditions) == 1
            else {"$and": where_conditions}
        )

        try:
            results = self.vectordb_service.get_chunks(limit=50, where=where)
            return [
                {
                    "chunk_id": r["chunk_id"],
                    "text": r["text"],
                    "metadata": r.get("metadata", {}),
                    "distance": None,
                    "structured_score": 1.0,
                }
                for r in results
            ]
        except Exception:
            logger.debug("Structured metadata search failed", exc_info=True)
            return []

    @staticmethod
    def _reciprocal_rank_fusion(
        ranked_lists: list[list[dict[str, Any]]],
        top_k: int = 30,
    ) -> list[dict[str, Any]]:
        """Fuse multiple ranked lists using Reciprocal Rank Fusion.

        RRF_score(chunk) = Σ  1 / (k + rank_in_list_i)

        This is parameter-free (k=60 is standard) and handles
        heterogeneous score distributions gracefully.
        """

        # Accumulate RRF scores
        rrf_scores: dict[str, float] = {}
        chunk_data: dict[str, dict[str, Any]] = {}

        for ranked_list in ranked_lists:
            for rank, item in enumerate(ranked_list):
                chunk_id = item.get("chunk_id", "")
                if not chunk_id:
                    continue
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (
                    1.0 / (RRF_K + rank + 1)
                )
                # Keep the richest metadata version
                if chunk_id not in chunk_data:
                    chunk_data[chunk_id] = dict(item)

        # Sort by RRF score
        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

        logger.info("=" * 80)
        logger.info("RRF FINAL RANKING")

        for rank, chunk_id in enumerate(sorted_ids[:10], start=1):
            item = chunk_data[chunk_id]
            logger.info(
            "%d | %.4f | %s | %s",
            rank,
            rrf_scores[chunk_id],
        item.get("metadata", {}).get("filename"),
        item.get("text", "")[:120].replace("\n", " "),
    )

        results: list[dict[str, Any]] = []
        for chunk_id in sorted_ids[:top_k]:
            item = chunk_data[chunk_id]
            item["rrf_score"] = round(rrf_scores[chunk_id], 6)
            results.append(item)

        return results

    def _format_fused_results(
        self,
        fused: list[dict[str, Any]],
        analyzed: AnalyzedQuery,
    ) -> list[RetrievalResult]:
        """Convert RRF-fused results into the public RetrievalResult format."""

        results: list[RetrievalResult] = []
        for item in fused:
            metadata = dict(item.get("metadata") or {})
            metadata["retrieval_mode"] = "hybrid_rrf"
            metadata["rrf_score"] = item.get("rrf_score", 0.0)
            metadata["intent"] = analyzed.intent.value

            if "bm25_score" in item:
                metadata["bm25_score"] = item["bm25_score"]
            if "structured_score" in item:
                metadata["structured_score"] = item["structured_score"]

            distance = item.get("distance")
            rrf_score = item.get("rrf_score", 0.0)

            results.append({
                "chunk_id": item["chunk_id"],
                "text": item.get("text", ""),
                "page_start": self._metadata_int(metadata.get("page_start")),
                "page_end": self._metadata_int(metadata.get("page_end")),
                "metadata": metadata,
                "distance": float(distance) if distance is not None else None,
                "score": round(rrf_score, 4),
            })

        return results

    # ── Validation helpers ────────────────────────────────────────────

    @staticmethod
    def _validate_question(question: str) -> str:
        if not isinstance(question, str):
            raise RetrievalValidationError("Question must be a string.")
        clean_question = question.strip()
        if not clean_question:
            raise RetrievalValidationError("Question cannot be empty.")
        return clean_question

    @staticmethod
    def _validate_top_k(top_k: int) -> int:
        if not isinstance(top_k, int):
            raise RetrievalValidationError("top_k must be an integer.")
        if top_k <= 0:
            raise RetrievalValidationError("top_k must be greater than 0.")
        if top_k > 100:
            raise RetrievalValidationError("top_k cannot exceed 100.")
        return top_k

    @staticmethod
    def _metadata_int(value: Any) -> int | None:
        if value is None or value == -1:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_identifier(value: Any) -> str:
        return str(value).strip().lower()
