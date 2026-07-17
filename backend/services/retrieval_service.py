"""Production-grade hybrid retrieval for INDUS MIND.

Executes search queries across three independent retrieval channels 
(dense vector, BM25 sparse, and structured metadata) according to the
RetrievalStrategy defined in the QueryPlan.
"""

import logging
from typing import Any, TypedDict

import backend.config as config
from backend.services.bm25_service import BM25Service
from backend.services.document_selector import DocumentSelection
from backend.services.embedding_service import EmbeddingService
from backend.services.query_understanding import QueryIntent, QueryPlan, RetrievalStrategy
from backend.services.vectordb_service import VectorDBService
from backend.services.query_expander import SearchQuery

logger = logging.getLogger(__name__)

RRF_K = getattr(config, "RRF_K", 60)
MAX_SEMANTIC_CANDIDATES = getattr(config, "MAX_SEMANTIC_CANDIDATES", 50)
BM25_TOP_K = getattr(config, "BM25_TOP_K", 50)

STRUCTURED_METADATA_FIELDS = {
    "problem_solution_mapping": "problem_statement_number",
    "structural_lookup": "problem_statement_number", # Default mapping, can be expanded
}


class RetrievalResult(TypedDict):
    """One hybrid retrieval result returned by the executor."""

    chunk_id: str
    text: str
    page_start: int | None
    page_end: int | None
    metadata: dict[str, Any]
    distance: float | None
    score: float


class RetrievalServiceError(Exception):
    """Base exception for all retrieval service errors."""


class HybridRetrievalExecutor:
    """Execute search queries across channels with strategy-aware orchestration."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vectordb_service: VectorDBService,
        bm25_service: BM25Service | None = None,
    ) -> None:
        self.embedding_service = embedding_service
        self.vectordb_service = vectordb_service
        self.bm25_service = bm25_service or BM25Service()

    def execute(
        self, query_plan: QueryPlan, user_role: str = "public"
    ) -> list[RetrievalResult]:
        """Execute the query plan and return fused candidates for non-multi-query strategies."""

        strategy = query_plan.retrieval_strategy
        scope = query_plan.document_selection
        
        logger.info(
            "Executing retrieval: strategy=%s scope=%s queries=%d",
            strategy.value,
            scope.scope.value,
            len(query_plan.search_queries),
        )

        if strategy == RetrievalStrategy.STRUCTURED:
            return self._execute_structured(query_plan, scope, user_role)

        if strategy == RetrievalStrategy.EXHAUSTIVE:
            return self._execute_exhaustive(query_plan, scope, user_role)

        if not query_plan.search_queries:
            return []
            
        return self.execute_query(query_plan.search_queries[0], query_plan.intent, scope, user_role)

    def execute_query(
        self, search_query: SearchQuery, intent: QueryIntent, scope: DocumentSelection, user_role: str
    ) -> list[RetrievalResult]:
        """Standard hybrid retrieval for a single overarching query."""
        
        target_docs = scope.selected_ids
        if search_query.target_document_id and not scope.is_strict:
            target_docs = [search_query.target_document_id]
            
        where = self._build_where(target_docs, None, user_role)

        dense = self._dense_search(search_query.text, where, MAX_SEMANTIC_CANDIDATES)
        bm25 = self._bm25_search(search_query.text, target_docs, BM25_TOP_K)

        fused = self._reciprocal_rank_fusion([dense, bm25], top_k=30)
        
        # Apply search query weight
        for candidate in fused:
            candidate["rrf_score"] = candidate.get("rrf_score", 0.0) * search_query.weight
            # Annotate with target entity if present
            if search_query.target_entity:
                candidate["target_entity"] = search_query.target_entity
                
        return self._format_results(fused, intent)

    # ── Strategy Implementations ──────────────────────────────────────

    def _execute_exhaustive(
        self, query_plan: QueryPlan, scope: DocumentSelection, user_role: str
    ) -> list[RetrievalResult]:
        """Search each document independently to ensure coverage."""
        
        if not scope.selected_ids or not query_plan.search_queries:
            if not query_plan.search_queries:
                return []
            return self.execute_query(query_plan.search_queries[0], query_plan.intent, scope, user_role)

        per_doc_results: list[dict[str, Any]] = []
        per_doc_k = max(5, 30 // len(scope.selected_ids))
        
        search_query = query_plan.search_queries[0]

        for doc_id in scope.selected_ids:
            where = self._build_where([doc_id], None, user_role)
            dense = self._dense_search(search_query.text, where, 15)
            bm25 = self._bm25_search(search_query.text, [doc_id], 15)
            
            fused = self._reciprocal_rank_fusion([dense, bm25], top_k=per_doc_k)
            per_doc_results.extend(fused)

        per_doc_results.sort(key=lambda x: x.get("rrf_score", 0.0), reverse=True)
        return self._format_results(per_doc_results, query_plan.intent)

    def _execute_structured(
        self, query_plan: QueryPlan, scope: DocumentSelection, user_role: str
    ) -> list[RetrievalResult]:
        """Metadata-only search for structured navigational queries."""
        
        results: list[dict[str, Any]] = []
        field_name = STRUCTURED_METADATA_FIELDS.get(query_plan.intent.value)
        
        if field_name:
            target_entity = next(
                (e for e in query_plan.entities if e.entity_type.value in query_plan.intent.value), 
                None
            )
            
            if target_entity:
                where = self._build_where(
                    scope.selected_ids, 
                    {field_name: target_entity.normalized},
                    user_role
                )
                
                try:
                    chunks = self.vectordb_service.get_chunks(limit=20, where=where)
                    for chunk in chunks:
                        chunk["rrf_score"] = 1.0  
                        chunk["structured_score"] = 1.0
                        results.append(chunk)
                except Exception as exc:
                    logger.warning("Structured lookup failed: %s", exc)

        if not results and self._has_semantic_content(query_plan.original_query) and query_plan.search_queries:
            logger.info("Structured lookup found 0 results, falling back to SINGLE strategy.")
            return self.execute_query(query_plan.search_queries[0], query_plan.intent, scope, user_role)

        return self._format_results(results, query_plan.intent)

    # ── Fusion and Formatting ──────────────────────────────────────────

    @staticmethod
    def _reciprocal_rank_fusion(
        ranked_lists: list[list[dict[str, Any]]], top_k: int = 30
    ) -> list[dict[str, Any]]:
        """Fuse multiple ranked lists using Reciprocal Rank Fusion."""
        
        rrf_scores: dict[str, float] = {}
        chunk_data: dict[str, dict[str, Any]] = {}

        for ranked_list in ranked_lists:
            for rank, item in enumerate(ranked_list):
                chunk_id = item.get("chunk_id")
                if not chunk_id:
                    continue
                    
                rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + (1.0 / (RRF_K + rank + 1))
                if chunk_id not in chunk_data:
                    chunk_data[chunk_id] = dict(item)

        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)

        results = []
        for chunk_id in sorted_ids[:top_k]:
            item = chunk_data[chunk_id]
            item["rrf_score"] = round(rrf_scores[chunk_id], 6)
            results.append(item)

        print("\n[RAG DEBUG] ====================================================")
        print("[RAG DEBUG] STEP 6 - Reciprocal Rank Fusion")
        dense_count = len(ranked_lists[0]) if len(ranked_lists) > 0 else 0
        bm25_count = len(ranked_lists[1]) if len(ranked_lists) > 1 else 0
        print(f"[RAG DEBUG] Dense Results Count: {dense_count}")
        print(f"[RAG DEBUG] BM25 Count: {bm25_count}")
        print(f"[RAG DEBUG] Final RRF Count: {len(results)}")
        print("[RAG DEBUG] ====================================================\n")

        return results

    def _format_results(self, chunks: list[dict[str, Any]], intent: QueryIntent) -> list[RetrievalResult]:
        """Format the internal chunk representation for API output."""
        
        formatted: list[RetrievalResult] = []
        for chunk in chunks:
            metadata = dict(chunk.get("metadata", {}))
            metadata["intent"] = intent.value
            
            # Preserve target entity if added
            if "target_entity" in chunk:
                metadata["target_entity"] = chunk["target_entity"]
            
            formatted.append({
                "chunk_id": chunk.get("chunk_id", ""),
                "text": chunk.get("text", ""),
                "page_start": self._metadata_int(metadata.get("page_start")),
                "page_end": self._metadata_int(metadata.get("page_end")),
                "metadata": metadata,
                "distance": chunk.get("distance"),
                "score": chunk.get("rrf_score", 0.0),
            })
            
        return formatted

    # ── Search Channels ───────────────────────────────────────────────

    def _dense_search(self, query: str, where: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
        """Execute vector search."""
        
        print("\n======== CHROMA ========")
        print(f"Applied where filter:\n{where}")
        print("========================\n")

        print("\n[RAG DEBUG] ====================================================")
        print("[RAG DEBUG] STEP 4 - Vector Search")
        print("[RAG DEBUG] Embedding Search Started")

        try:
            query_embedding = self.embedding_service.generate_embedding(query, is_query=True)
            results = self.vectordb_service.search(
                query_embedding=query_embedding, top_k=top_k, where=where
            )
            
            print(f"[RAG DEBUG] Retrieved Chunk Count: {len(results)}")
            for r in results:
                meta = r.get("metadata", {})
                print(f"[RAG DEBUG] Document ID: {meta.get('document_id')}")
                print(f"[RAG DEBUG] Document Name: {meta.get('filename')}")
                print(f"[RAG DEBUG] Chunk ID: {r.get('chunk_id')}")
                print(f"[RAG DEBUG] Page Number: {meta.get('page_start')}")
                print(f"[RAG DEBUG] Similarity Score: {r.get('distance')}")
            print("[RAG DEBUG] ====================================================\n")

            return [
                {
                    "chunk_id": r["chunk_id"],
                    "text": r["text"],
                    "metadata": r.get("metadata", {}),
                    "distance": r.get("distance"),
                }
                for r in results
            ]
        except Exception as exc:
            logger.warning("Dense search failed: %s", exc)
            return []

    def _bm25_search(self, query: str, document_ids: list[str], top_k: int) -> list[dict[str, Any]]:
        """Execute sparse keyword search."""
        
        if not self.bm25_service or self.bm25_service.index_size == 0:
            return []
            
        try:
            results = self.bm25_service.search(query=query, top_k=top_k, document_ids=document_ids)
            
            print("\n[RAG DEBUG] ====================================================")
            print("[RAG DEBUG] STEP 5 - BM25 Search")
            print(f"[RAG DEBUG] Retrieved BM25 Count: {len(results)}")
            print(f"[RAG DEBUG] Document IDs: {document_ids}")
            print("[RAG DEBUG] ====================================================\n")

            return [
                {
                    "chunk_id": r["chunk_id"],
                    "text": r["text"],
                    "metadata": r.get("metadata", {}),
                    "bm25_score": r["score"],
                }
                for r in results
            ]
        except Exception as exc:
            logger.warning("BM25 search failed: %s", exc)
            return []

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_where(
        document_ids: list[str] | None, 
        additional_filters: dict[str, Any] | None,
        user_role: str
    ) -> dict[str, Any]:
        """Build ChromaDB where clause with role and document constraints."""
        
        conditions = []
        
        if document_ids:
            conditions.append({"document_id": {"$in": document_ids}})
            
        if additional_filters:
            conditions.append(additional_filters)
            
        allowed_roles = ["public"]
        if user_role == "engineer":
            allowed_roles = ["public", "engineer"]
        elif user_role == "admin":
            allowed_roles = ["public", "engineer", "admin"]
            
        conditions.append({"access_level": {"$in": allowed_roles}})
        
        if not conditions:
            return {}
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    @staticmethod
    def _metadata_int(value: Any) -> int | None:
        if value is None or value == -1:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _has_semantic_content(query: str) -> bool:
        words = [w for w in query.split() if w.lower() not in {"problem", "statement", "page", "section", "chapter", "number", "no"}]
        return len(words) > 1

RetrievalService = HybridRetrievalExecutor
