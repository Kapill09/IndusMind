"""Real BM25 sparse retrieval for the INDUS MIND hybrid search pipeline.

Replaces the pseudo-keyword scoring with a proper BM25 Okapi implementation
backed by a precomputed inverted index.  The index is built at ingestion time
and persisted to disk so it survives restarts.
"""

import logging
import os
import pickle
import re
import threading
from pathlib import Path
from typing import Any, TypedDict

from rank_bm25 import BM25Okapi

import backend.config as config

logger = logging.getLogger(__name__)

_DEFAULT_INDEX_DIR = Path(getattr(config, "BM25_INDEX_PATH", "./data/bm25"))
if not _DEFAULT_INDEX_DIR.is_absolute():
    _DEFAULT_INDEX_DIR = Path(__file__).resolve().parents[2] / _DEFAULT_INDEX_DIR

_INDEX_FILE = "bm25_index.pkl"

# Simple tokenizer: lowercase alphanumeric tokens, preserving dotted numbers.
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[0-9]+)?")

_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "in", "is", "it", "its", "of", "on", "or", "the",
    "to", "was", "were", "what", "when", "where", "which", "who", "why",
    "will", "with", "this", "that", "than",
})


class BM25Result(TypedDict):
    """One BM25 retrieval result."""

    chunk_id: str
    text: str
    score: float
    metadata: dict[str, Any]


class BM25ServiceError(Exception):
    """Base exception for BM25 service errors."""


class BM25Service:
    """BM25 Okapi sparse retrieval over the indexed chunk corpus.

    The service maintains an in-memory BM25 index that is persisted to disk
    after every mutation.  All public methods are thread-safe.

    Args:
        index_dir: Directory for persisting the BM25 index.
    """

    def __init__(self, *, index_dir: Path | str = _DEFAULT_INDEX_DIR) -> None:
        self._index_dir = Path(index_dir)
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._index_dir / _INDEX_FILE
        self._lock = threading.Lock()

        # Internal state
        self._corpus_tokens: list[list[str]] = []
        self._chunk_metas: list[dict[str, Any]] = []  # chunk_id, text, metadata per entry
        self._bm25: BM25Okapi | None = None

        self._load_index()

    # ── Public API ────────────────────────────────────────────────────

    def build_index(self, chunks: list[dict[str, Any]]) -> int:
        """Build or rebuild the entire BM25 index from scratch.

        Args:
            chunks: List of chunk dicts, each with ``chunk_id``, ``text``, and
                    ``metadata`` keys.

        Returns:
            Number of chunks indexed.
        """

        with self._lock:
            self._corpus_tokens = []
            self._chunk_metas = []

            for chunk in chunks:
                text = str(chunk.get("text", ""))
                tokens = self._tokenize(text)
                self._corpus_tokens.append(tokens)
                self._chunk_metas.append({
                    "chunk_id": str(chunk.get("chunk_id", "")),
                    "text": text,
                    "metadata": dict(chunk.get("metadata") or {}),
                })

            self._rebuild_bm25()
            self._persist_index()

        logger.info("BM25 index built: chunks=%s", len(self._corpus_tokens))
        return len(self._corpus_tokens)

    def add_document(self, chunks: list[dict[str, Any]]) -> int:
        """Incrementally add a document's chunks to the BM25 index.

        Args:
            chunks: List of chunk dicts for one document.

        Returns:
            Total number of chunks in the index after addition.
        """

        if not chunks:
            return len(self._corpus_tokens)

        with self._lock:
            for chunk in chunks:
                text = str(chunk.get("text", ""))
                tokens = self._tokenize(text)
                self._corpus_tokens.append(tokens)
                self._chunk_metas.append({
                    "chunk_id": str(chunk.get("chunk_id", "")),
                    "text": text,
                    "metadata": dict(chunk.get("metadata") or {}),
                })

            self._rebuild_bm25()
            self._persist_index()

        logger.info("BM25 index updated: added=%s total=%s", len(chunks), len(self._corpus_tokens))
        return len(self._corpus_tokens)

    def remove_document(self, document_id: str) -> int:
        """Remove all chunks belonging to a document and rebuild the index.

        Args:
            document_id: Document ID to remove.

        Returns:
            Number of chunks remaining after removal.
        """

        with self._lock:
            keep_tokens: list[list[str]] = []
            keep_metas: list[dict[str, Any]] = []

            for tokens, meta in zip(self._corpus_tokens, self._chunk_metas):
                if meta.get("metadata", {}).get("document_id") != document_id:
                    keep_tokens.append(tokens)
                    keep_metas.append(meta)

            removed = len(self._corpus_tokens) - len(keep_tokens)
            self._corpus_tokens = keep_tokens
            self._chunk_metas = keep_metas

            self._rebuild_bm25()
            self._persist_index()

        logger.info("BM25 document removed: document_id=%s removed=%s remaining=%s",
                     document_id, removed, len(self._corpus_tokens))
        return len(self._corpus_tokens)

    def search(
        self,
        query: str,
        top_k: int = 50,
        document_ids: list[str] | None = None,
    ) -> list[BM25Result]:
        """Score and return the top-K chunks using BM25.

        Args:
            query: User query string.
            top_k: Maximum results to return.
            document_ids: Optional whitelist of document IDs to restrict results.

        Returns:
            List of BM25Result dicts sorted by descending score.
        """

        if not self._bm25 or not self._corpus_tokens:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        with self._lock:
            scores = self._bm25.get_scores(query_tokens)

        # Pair scores with metadata and apply document filter
        scored: list[tuple[float, dict[str, Any]]] = []
        allowed = set(document_ids) if document_ids else None

        for idx, score in enumerate(scores):
            if score <= 0.0:
                continue
            meta = self._chunk_metas[idx]
            if allowed and meta.get("metadata", {}).get("document_id") not in allowed:
                continue
            scored.append((float(score), meta))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[BM25Result] = []
        for score, meta in scored[:top_k]:
            results.append({
                "chunk_id": meta["chunk_id"],
                "text": meta["text"],
                "score": round(score, 4),
                "metadata": meta["metadata"],
            })

        return results

    @property
    def index_size(self) -> int:
        """Number of chunks currently in the BM25 index."""
        return len(self._corpus_tokens)

    # ── Internal ──────────────────────────────────────────────────────

    def _rebuild_bm25(self) -> None:
        """Rebuild the BM25 model from the current corpus tokens."""
        if self._corpus_tokens:
            self._bm25 = BM25Okapi(self._corpus_tokens)
        else:
            self._bm25 = None

    def _persist_index(self) -> None:
        """Serialize index to disk."""
        try:
            with open(self._index_path, "wb") as f:
                pickle.dump({
                    "corpus_tokens": self._corpus_tokens,
                    "chunk_metas": self._chunk_metas,
                }, f)
        except Exception:
            logger.exception("Failed to persist BM25 index to %s", self._index_path)

    def _load_index(self) -> None:
        """Load a previously persisted index from disk."""
        if not self._index_path.exists():
            logger.info("No existing BM25 index found at %s", self._index_path)
            return

        try:
            with open(self._index_path, "rb") as f:
                data = pickle.load(f)
            self._corpus_tokens = data.get("corpus_tokens", [])
            self._chunk_metas = data.get("chunk_metas", [])
            self._rebuild_bm25()
            logger.info("BM25 index loaded: chunks=%s", len(self._corpus_tokens))
        except Exception:
            logger.exception("Failed to load BM25 index from %s", self._index_path)
            self._corpus_tokens = []
            self._chunk_metas = []
            self._bm25 = None

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase terms with stopword removal."""
        return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]
