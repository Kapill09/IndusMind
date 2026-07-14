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
                config, "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
            )
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
        self, question: str, chunks: list[dict[str, Any]], top_k: int = 5
    ) -> list[dict[str, Any]]:
        """Rerank chunks using the cross-encoder, preserving structured retrieval dominance.

        Args:
            question: The user question.
            chunks: List of candidate chunks from Hybrid Retrieval.
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

        for i, chunk in enumerate(chunks):
            metadata = chunk.setdefault("metadata", {})
            
            reranker_score = float(scores[i])
            metadata["reranker_score"] = round(reranker_score, 4)

            combined_score = chunk.get("score", 0.0)
            metadata["combined_score"] = round(combined_score, 4)

            structured_score = metadata.get("structured_score", 0.0)

            # Final score calculation: primarily based on reranker, but structured
            # matches get a massive boost to ensure they never lose to pure semantic matches.
            final_score = reranker_score
            if structured_score > 0.5:
                # Add a very large constant to ensure it stays at the top
                final_score += 100.0 + (structured_score * 10)

            metadata["final_score"] = round(final_score, 4)
            chunk["score"] = round(final_score, 4)

        # Sort descending by final score
        chunks.sort(key=lambda x: x["score"], reverse=True)

        return chunks[:top_k]
