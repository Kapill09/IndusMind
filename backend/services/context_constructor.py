"""Context construction for INDUS MIND retrieval.

Builds the final context window from reranked chunks. Responsible for:
1. Deduplication (removing exact duplicates)
2. Sentence completion (fetching neighbors ONLY if a chunk ends mid-sentence)
3. Budget enforcement (limiting context to approx 3500 tokens)
4. Formatting (preserving citations and metadata for the LLM)

Note: This refactored version strictly preserves CrossEncoder ranking
by never reordering the chunks.
"""

from torch import chunk
import logging
from typing import Any

from backend.services.query_understanding import QueryPlan
from backend.services.vectordb_service import VectorDBService

logger = logging.getLogger(__name__)


class ContextConstructor:
    """Build the final context window from reranked chunks."""

    def __init__(self, vectordb_service: VectorDBService):
        self.vectordb_service = vectordb_service

    def construct(
        self,
        chunks: list[dict[str, Any]],
        query_plan: QueryPlan,
        max_tokens: int = 3500,
    ) -> list[dict[str, Any]]:
        """Construct the context window.

        Args:
            chunks: Reranked candidate chunks.
            query_plan: The plan driving this retrieval.
            max_tokens: Maximum allowed tokens for context.

        Returns:
            The final list of context chunks formatted for the LLM.
        """
        if not chunks:
            return []

        # 1. Remove duplicate chunks while preserving the original ranking order
        deduped = self._deduplicate(chunks)
        
        # 2. Expand neighbors ONLY to complete sentences, preserving order
        completed = self._expand_and_merge_neighbors(deduped)
        
        # 3. Enforce the budget of ~3500 tokens as requested
        budgeted = self._enforce_budget(completed, max_tokens)
        
        return budgeted

    # ── Pipeline Steps ────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove exact duplicates by chunk_id while preserving rank order."""
        seen = set()
        deduped = []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            if not chunk_id or chunk_id not in seen:
                if chunk_id:
                    seen.add(chunk_id)
                deduped.append(chunk.copy())
        return deduped

    def _expand_and_merge_neighbors(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Identify chunks that end mid-sentence, fetch their next consecutive chunk,
        and merge the text to complete the sentence. Strictly keeps CrossEncoder order.
        """
        chunk_map = {c.get("chunk_id"): c for c in chunks if c.get("chunk_id")}
        needs_next = {}
        
        # Identify chunks requiring completion
        for idx, chunk in enumerate(chunks):
            text = str(chunk.get("text", "")).strip()
            metadata = chunk.get("metadata", {})
            doc_id = metadata.get("document_id")
            chunk_index = metadata.get("chunk_index")
            
            if self._is_incomplete_sentence(text) and doc_id and chunk_index is not None:
                try:
                    next_idx = int(chunk_index) + 1
                    next_id = f"{doc_id}:chunk-{next_idx:04d}"
                    needs_next[idx] = {"doc_id": doc_id, "next_idx": next_idx, "next_id": next_id}
                except (ValueError, TypeError):
                    pass

        # Fetch any neighbors we don't already have in memory
        missing_filters = []
        for req in needs_next.values():
            if req["next_id"] not in chunk_map:
                missing_filters.append({"$and": [{"document_id": req["doc_id"]}, {"chunk_index": req["next_idx"]}]})
                
        if missing_filters:
            try:
                for i in range(0, len(missing_filters), 20):
                    batch = missing_filters[i:i+20]
                    where = {"$or": batch} if len(batch) > 1 else batch[0]
                    neighbors = self.vectordb_service.get_chunks(limit=len(batch), where=where)
                    for n in neighbors:
                        if n.get("chunk_id"):
                            chunk_map[n["chunk_id"]] = n
            except Exception as exc:
                logger.warning("ContextConstructor: failed to fetch completing neighbors: %s", exc)

        completed_chunks = []
        consumed_ids = set()
        
        # Merge chunks in original ranked order
        for idx, chunk in enumerate(chunks):
            chunk_id = chunk.get("chunk_id")
            if chunk_id in consumed_ids:
                continue
                
            new_chunk = chunk.copy()
            current_text = str(new_chunk.get("text", "")).strip()
            
            if idx in needs_next:
                req = needs_next[idx]
                next_id = req["next_id"]
                if next_id in chunk_map and next_id not in consumed_ids:
                    neighbor = chunk_map[next_id]
                    next_text = str(neighbor.get("text", "")).strip()
                    current_text = self._merge_texts(current_text, next_text)
                    consumed_ids.add(next_id)
            
            new_chunk["text"] = current_text
            consumed_ids.add(chunk_id)
            completed_chunks.append(new_chunk)
            
        return completed_chunks

    @staticmethod
    def _is_incomplete_sentence(text: str) -> bool:
        """Check if text appears to end mid-sentence."""
        if not text:
            return False
        # If it doesn't end with standard punctuation, it's likely cut off
        return text[-1] not in {'.', '!', '?', '"', "'", '\n', ']', ')'}

    @staticmethod
    def _merge_texts(prev_text: str, curr_text: str) -> str:
        """Merge two texts, removing any overlapping characters at the boundary."""
        suffix = prev_text[-150:]
        if len(suffix) > 20:
            idx = curr_text.find(suffix[:50])
            if idx != -1 and idx < 300:
                overlap_len = len(prev_text) - prev_text.rfind(curr_text[idx:idx+50])
                if overlap_len > 0:
                    return prev_text + " " + curr_text[idx + overlap_len:].strip()
        return prev_text + " " + curr_text

    @staticmethod
    def _enforce_budget(chunks: list[dict[str, Any]], max_tokens: int) -> list[dict[str, Any]]:
        """Enforce the token budget (approx 4 chars per token).
        We enforce ~3500 tokens limit as per requirements.
        """
        # Hard limit to 3500 to satisfy the specific requirement, or max_tokens if it's lower.
        budget_tokens = min(max_tokens, 3500)
        max_chars = budget_tokens * 4
        
        budgeted = []
        current_chars = 0
        
        for chunk in chunks:
            text = chunk.get("text", "")
            chars = len(text)
            if current_chars + chars > max_chars:
                if current_chars == 0:
                    # Keep at least one chunk (truncated) if it's too large
                    
                    cut = text[:max_chars]

                    last_period = max(
                        cut.rfind("."),
                        cut.rfind("!"),
                        cut.rfind("?")
                    )

                    if last_period > 500:
                        cut = cut[:last_period + 1]

                    chunk["text"] = cut
                    budgeted.append(chunk)
                break

            budgeted.append(chunk)
            current_chars += chars
            
        return budgeted

