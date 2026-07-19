"""Enterprise Cross-Encoder Reranker for retrieved chunks.

Provides strategy-aware reranking driven by the QueryPlan.
Enforces strict minimum scores and near-duplicate removal.
"""

import logging
import re
from time import perf_counter
from typing import Any

from sentence_transformers import CrossEncoder

import backend.config as config
from backend.services.query_understanding import QueryIntent, QueryPlan, RetrievalStrategy
from backend.services.entity_extractor import EntityType

logger = logging.getLogger(__name__)


class RerankerServiceError(Exception):
    """Base exception for reranker service errors."""


class RerankerService:
    """Strategy-aware Cross-Encoder Reranker."""

    _instance = None
    _model = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: str | None = None) -> None:
        if not hasattr(self, "_initialized"):
            self.model_name = model_name or getattr(
                config, "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-12-v2"
            )
            # -4.0 is typical cutoff for ms-marco cross-encoder
            self.min_score = getattr(config, "MIN_RERANKER_SCORE", -4.0)
            self._load_model()
            self._initialized = True

    def _load_model(self) -> None:
        """Load the cross-encoder model as a singleton."""
        if RerankerService._model is None:
            logger.info("Loading Cross-Encoder model: %s", self.model_name)
            try:
                started_at = perf_counter()
                RerankerService._model = CrossEncoder(self.model_name, max_length=512)
                logger.info(
                    "Loaded Cross-Encoder model in %dms",
                    int((perf_counter() - started_at) * 1000),
                )
            except Exception as exc:
                raise RerankerServiceError(
                    f"Failed to load Cross-Encoder model {self.model_name}"
                ) from exc

    def rerank(
        self,
        question: str,
        chunks: list[dict[str, Any]],
        top_k: int = 8,
        query_plan: QueryPlan | None = None,
    ) -> list[dict[str, Any]]:
        """Rerank chunks based on the retrieval strategy."""
        
        if not chunks:
            return []

        # ── Strategy 1: Structured Metadata ──────────────────────────────
        if query_plan and query_plan.retrieval_strategy == RetrievalStrategy.STRUCTURED:
            # Don't rerank structured results — metadata is authoritative
            logger.info("Reranker: Bypassing cross-encoder for STRUCTURED strategy.")
            return chunks[:top_k]

        # ── Standard Reranking ───────────────────────────────
        return self._rerank_standard(question, chunks, top_k)

    def _rerank_standard(
        self, question: str, chunks: list[dict[str, Any]], top_k: int
    ) -> list[dict[str, Any]]:
        """Standard cross-encoder scoring for a single query."""
        
        pairs = [(question, str(chunk.get("text", ""))) for chunk in chunks]

        try:
            started_at = perf_counter()
            scores = RerankerService._model.predict(pairs)
            logger.debug(
                "Cross-Encoder scored %d chunks in %dms",
                len(chunks), int((perf_counter() - started_at) * 1000),
            )
        except Exception:
            logger.exception("Reranker prediction failed, returning original order.")
            return chunks[:top_k]

        # Attach scores and filter
        filtered = []
        for i, chunk in enumerate(chunks):
            score = float(scores[i])
            chunk["score"] = round(score, 4)
            chunk.setdefault("metadata", {})["reranker_score"] = round(score, 4)
            
            if score >= self.min_score:
                filtered.append(chunk)

        if not filtered:
            logger.warning("All %d chunks scored below minimum threshold %.2f", len(chunks), self.min_score)
            # Fallback: keep top 2 so we don't completely fail, validator will catch garbage
            for i, chunk in enumerate(chunks):
                chunk["score"] = float(scores[i])
            filtered = sorted(chunks, key=lambda x: x["score"], reverse=True)[:2]
        else:
            filtered.sort(key=lambda x: x["score"], reverse=True)

        # Remove near-duplicates (>80% text overlap)
        deduped = self._remove_near_duplicates(filtered)
        final_results = deduped[:top_k]
        
        print("\n[RAG DEBUG] ====================================================")
        print("[RAG DEBUG] STEP 7 - Cross Encoder")
        for i, chunk in enumerate(final_results):
            meta = chunk.get("metadata", {})
            print(f"[RAG DEBUG] Chunk ID: {chunk.get('chunk_id')}")
            print(f"[RAG DEBUG] Document: {meta.get('document_id')}")
            print(f"[RAG DEBUG] Cross Encoder Score: {chunk.get('score')}")
            print(f"[RAG DEBUG] Ranking: {i + 1}")
        print("[RAG DEBUG] ====================================================\n")

        logger.info(
            "Reranker: scored=%d above_thresh=%d deduped=%d top_score=%.2f", 
            len(chunks), len(filtered), len(deduped), 
            deduped[0]["score"] if deduped else 0.0
        )

        return final_results

    def _remove_near_duplicates(
        self, chunks: list[dict[str, Any]], threshold: float = 0.8
    ) -> list[dict[str, Any]]:
        """Remove chunks with >threshold token overlap with a higher-ranked chunk."""
        
        result: list[dict[str, Any]] = []
        
        for chunk in chunks:
            is_dup = False
            chunk_tokens = set(re.findall(r'[a-z0-9]+', str(chunk.get("text", "")).lower()))
            
            for existing in result:
                existing_tokens = set(re.findall(r'[a-z0-9]+', str(existing.get("text", "")).lower()))
                if chunk_tokens and existing_tokens:
                    intersection = len(chunk_tokens & existing_tokens)
                    smaller = min(len(chunk_tokens), len(existing_tokens))
                    
                    # Prevent short title pages from being wrongly flagged as duplicates
                    if smaller > 15 and (intersection / smaller) > threshold:
                        is_dup = True
                        break
                        
            if not is_dup:
                result.append(chunk)
                
        return result
