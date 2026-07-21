"""Production-grade hybrid retrieval for INDUS MIND.

Executes search queries across three independent retrieval channels 
(dense vector, BM25 sparse, and structured metadata) according to the
RetrievalStrategy defined in the QueryPlan.
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

<<<<<<< HEAD
    def execute(
        self, query_plan: QueryPlan, user_role: str = "public"
    ) -> list[RetrievalResult]:
        """Execute the query plan and return fused candidates for non-multi-query strategies."""

        strategy = query_plan.retrieval_strategy
        scope = query_plan.document_selection
        
=======
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
        logger.info("Raw selected_document_ids received from the frontend: %s", document_ids)
        logger.info("=" * 80)

        clean_question = self._validate_question(question)
        clean_top_k = self._validate_top_k(top_k)
        clean_document_ids = sanitize_document_ids(document_ids)
        logger.info("Normalized selected_document_ids: %s", clean_document_ids)
        
        # Log first 5 docs in Chroma
        try:
            first_five = self.vectordb_service.collection.get(limit=5, include=["metadatas"])
            logger.info("--- FIRST 5 DOCUMENTS STORED IN CHROMA ---")
            for m in first_five.get("metadatas") or []:
                logger.info("document_id: %s | filename: %s", m.get("document_id"), m.get("filename"))
        except Exception as e:
            logger.info("Could not fetch first 5 documents from Chroma: %s", e)

        # ── Stage 1: Query Analysis ──────────────────────────────────
        analyzed = self.query_analyzer.full_analyze(clean_question)
>>>>>>> hackathon-final
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
            
        return self.execute_query(
            query_plan.search_queries[0],
            query_plan.intent,
            scope,
            user_role,
            query_plan=query_plan,
        )

    def execute_query(
        self,
        search_query: SearchQuery,
        intent: QueryIntent,
        scope: DocumentSelection,
        user_role: str,
        query_plan: QueryPlan | None = None,
    ) -> list[RetrievalResult]:
        """Standard hybrid retrieval for a single overarching query."""
        
        target_docs = scope.selected_ids
        if search_query.target_document_id and not scope.is_strict:
            target_docs = [search_query.target_document_id]
            
        where = self._build_where(target_docs, None, user_role)
        dense_top_k, bm25_top_k, fusion_top_k = self._adaptive_top_k(intent, search_query.text, query_plan)

        dense = self._dense_search(search_query.text, where, dense_top_k)
        bm25 = self._bm25_search(search_query.text, target_docs, bm25_top_k)

        fused = self._reciprocal_rank_fusion([dense, bm25], top_k=fusion_top_k)
        
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
            # Find the entity that matches the field name (e.g., problem_statement_number -> PROBLEM_STATEMENT)
            # or just take the first structural entity.
            target_entity = next(
                (e for e in query_plan.entities if e.entity_type.value in field_name), 
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

<<<<<<< HEAD
        return self._format_results(results, query_plan.intent)

    # ── Fusion and Formatting ──────────────────────────────────────────
=======
        # ── Final scope enforcement ──────────────────────────────────
        logger.info("--- TOP 10 RETRIEVED CHUNKS (Pre-Filter) ---")
        for i, res in enumerate(all_results[:10], start=1):
            doc_id = res["metadata"].get("document_id")
            passed = (not clean_document_ids) or (doc_id in clean_document_ids)
            logger.info("Rank %d | chunk_id: %s | document_id: %s | score: %.4f | passed_filter: %s", i, res.get("chunk_id"), doc_id, res.get("score", 0.0), passed)

        logger.info("--- CHUNK COUNT PER DOCUMENT (Pre-Filter) ---")
        doc_counts = {}
        for res in all_results:
            doc_id = res["metadata"].get("document_id")
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
        for doc_id, count in doc_counts.items():
            logger.info("document_id: %s -> %d chunks", doc_id, count)

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
        logger.info("Exact where filter sent to Chroma: %s", where)
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
        logger.info("Total chunks returned by Chroma: %d", len(dense_ranked))
        for chunk in dense_ranked:
            meta = chunk.get("metadata", {})
            logger.info(
                "chunk_id: %s | document_id: %s | filename: %s | page: %s",
                chunk.get("chunk_id"),
                meta.get("document_id"),
                meta.get("filename"),
                meta.get("page_start")
            )
        logger.info("=" * 80)

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
>>>>>>> hackathon-final

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

<<<<<<< HEAD
        results = []
=======
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
>>>>>>> hackathon-final
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
                "text": chunk.get("text","").strip(),
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
            results = sorted(
            results,
            key=lambda x: x.get("distance", 9999)
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
<<<<<<< HEAD
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
=======
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
>>>>>>> hackathon-final

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

    @staticmethod
    def _adaptive_top_k(intent: QueryIntent, query: str, query_plan: QueryPlan | None = None) -> tuple[int, int, int]:
        lowered = query.lower()
        if re.search(r"\b\d+\b|\bnumber\b|\bcount\b", lowered):
            return 10, 10, 12

        if intent == QueryIntent.COMPARISON or intent.value == "cross_document_comparison":
            return 12, 10, 15

        if intent == QueryIntent.SUMMARIZATION:
            return 18, 18, 20

        if intent == QueryIntent.DEFINITION:
            return 8, 8, 10

        if intent == QueryIntent.EXPLANATION:
            return 10, 10, 12

        if intent in (QueryIntent.PROCEDURE, QueryIntent.STEP_BY_STEP_GUIDE, QueryIntent.WORKFLOW, QueryIntent.TROUBLESHOOTING, QueryIntent.RECOMMENDATION):
            return 6, 6, 8

        if intent == QueryIntent.STRUCTURAL_LOOKUP:
            return 3, 3, 4

        return 5, 5, 6

RetrievalService = HybridRetrievalExecutor
