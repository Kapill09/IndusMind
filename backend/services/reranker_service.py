import logging
from time import perf_counter
from typing import Any

from sentence_transformers import CrossEncoder

import backend.config as config

logger = logging.getLogger(__name__)


class RerankerServiceError(Exception):
    """Base exception for reranker service errors."""


class RerankerService:
    """Enterprise Cross-Encoder Reranker for retrieved chunks.

    Loads the cross-encoder model as a singleton and provides scoring
    without breaking encapsulation of RetrievalService.

    The reranker uses genuine cross-encoder relevance scores without
    artificial boosts.  Structured metadata matches are handled via
    guaranteed slots instead of score hacking.
    """

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
            self._min_score = getattr(config, "MIN_RERANKER_SCORE", -4.0)
            self._guaranteed_slots = getattr(config, "RERANKER_GUARANTEED_STRUCTURED_SLOTS", 2)
            self._load_model()
            self._initialized = True

    def _load_model(self) -> None:
        """Load the cross-encoder model only once and cache it."""
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
        self, question: str, chunks: list[dict[str, Any]], top_k: int = 8
    ) -> list[dict[str, Any]]:
        """Rerank chunks using the cross-encoder with guaranteed slots for structured matches.

        Architecture:
        1. Score all chunks with the cross-encoder (genuine relevance)
        2. Identify structured metadata matches (exact section/problem matches)
        3. Reserve top N slots for structured matches (if they exist)
        4. Fill remaining slots from cross-encoder ranking
        5. Apply minimum score threshold to filter noise

        Args:
            question: The user question.
            chunks: List of candidate chunks from hybrid retrieval.
            top_k: Number of chunks to return.

        Returns:
            List of reranked and rescored chunks.
        """
        if not chunks:
            return []

        pairs = [(question, str(chunk.get("text", ""))) for chunk in chunks]

        try:
            rerank_started_at = perf_counter()
            scores = RerankerService._model.predict(pairs)
            logger.info(
                "Cross-Encoder scoring completed in %dms for %d chunks",
                int((perf_counter() - rerank_started_at) * 1000),
                len(chunks),
            )
        except Exception:
            logger.exception("Reranker model prediction failed, falling back to original ordering.")
            return chunks[:top_k]

        # Attach cross-encoder scores to chunks
        for i, chunk in enumerate(chunks):
            metadata = chunk.setdefault("metadata", {})
            reranker_score = float(scores[i])
            metadata["reranker_score"] = round(reranker_score, 4)
            chunk["score"] = round(reranker_score, 4)
            print("\n===== RERANK RESULTS =====")

            for c in sorted(chunks, key=lambda x: x["score"], reverse=True):

                print(c["score"])

                print(c["text"][:250])

                print("-"*60)

        # Separate structured matches from regular results
        structured_matches: list[dict[str, Any]] = []
        regular_chunks: list[dict[str, Any]] = []

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            structured_score = float(metadata.get("structured_score", 0.0) or 0.0)
            if structured_score > 0.5:
                structured_matches.append(chunk)
            else:
                regular_chunks.append(chunk)

        # Sort each group by cross-encoder score (genuine relevance)
        structured_matches.sort(key=lambda x: x["score"], reverse=True)
        regular_chunks.sort(key=lambda x: x["score"], reverse=True)

        # Apply minimum score threshold to regular chunks
        # regular_chunks = [c for c in regular_chunks if c["score"] >= self._min_score]
        # TEMPORARY
        logger.info("Skipping minimum score filtering.")

        regular_chunks = regular_chunks

        # Build final list: guaranteed slots for structured matches, then fill from regular
        final: list[dict[str, Any]] = []
        guaranteed_count = min(self._guaranteed_slots, len(structured_matches))

        # Add guaranteed structured matches
        for chunk in structured_matches[:guaranteed_count]:
            final.append(chunk)

        # Fill remaining slots from regular chunks (and any remaining structured matches)
        remaining_pool = structured_matches[guaranteed_count:] + regular_chunks
        
        logger.info("Structured matches = %d", len(structured_matches))
        logger.info("Regular chunks = %d", len(regular_chunks))
        logger.info("Remaining pool = %d", len(remaining_pool))

        remaining_pool.sort(key=lambda x: x["score"], reverse=True)

        for chunk in remaining_pool:
            if len(final) >= top_k:
                break
            if chunk["chunk_id"] not in {c["chunk_id"] for c in final}:
                final.append(chunk)
            logger.info("Current final size = %d", len(final))

        logger.info(
            "Reranking completed: candidates=%d structured=%d guaranteed=%d final=%d",
            len(chunks),
            len(structured_matches),
            guaranteed_count,
            len(final),
        )
        logger.info("FINAL CHUNKS")

        for c in final:
            logger.info(
                "%s | %.4f",
                c["chunk_id"],
                c["score"]
            )
        return final
