"""Context construction for INDUS MIND retrieval.

Builds the final context window from reranked chunks.  Responsible for:
1. Neighbor expansion (fetching adjacent chunks for continuity)
2. Overlap removal (stripping duplicated text at chunk boundaries)
3. Document grouping (sorting by document and page)
4. Token budget enforcement
"""

import logging
from collections import defaultdict
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
        max_tokens: int = 6000,
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

        # Step 1: Deduplicate (exact chunk_id)
        deduped = self._deduplicate(chunks)

        # Step 2: Fetch neighboring chunks for context continuity
        expanded = self._expand_neighbors(deduped)

        # Step 3: Remove overlapping text at chunk boundaries
        cleaned = self._remove_boundary_overlap(expanded)

        # Step 4: Group by document, order by chunk index
        grouped = self._group_and_order(cleaned)

        # Step 5: Enforce token budget (simple heuristic)
        budgeted = self._enforce_budget(grouped, max_tokens)

        # Step 6: Add document separators for LLM clarity
        formatted = self._format_for_llm(budgeted)

        return formatted

    # ── Pipeline Steps ────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove exact duplicates by chunk_id."""
        seen = set()
        deduped = []
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            if not chunk_id or chunk_id not in seen:
                if chunk_id:
                    seen.add(chunk_id)
                deduped.append(chunk.copy())
        return deduped

    def _expand_neighbors(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fetch immediate neighbors (chunk_index ± 1) for context continuity.

        We only fetch neighbors if the query is a definition/explanation or
        if the chunk is particularly high scoring, to avoid bloating context.
        """
        expanded = list(chunks)
        seen_ids = {c.get("chunk_id") for c in chunks if c.get("chunk_id")}

        # Build query filters for all required neighbors to fetch in bulk
        neighbor_filters = []
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            doc_id = metadata.get("document_id")
            chunk_index = metadata.get("chunk_index")
            score = chunk.get("score", 0)

            # Skip neighbor expansion for low-scoring chunks
            if not doc_id or chunk_index is None or score < -1.0:
                continue
            
            try:
                chunk_index = int(chunk_index)
            except (ValueError, TypeError):
                continue

            for offset in [-1, 1]:
                neighbor_idx = chunk_index + offset
                if neighbor_idx < 1:
                    continue

                neighbor_id = f"{doc_id}:chunk-{neighbor_idx:04d}"
                if neighbor_id not in seen_ids:
                    seen_ids.add(neighbor_id)
                    neighbor_filters.append(
                        {"$and": [{"document_id": doc_id}, {"chunk_index": neighbor_idx}]}
                    )

        if not neighbor_filters:
            return expanded

        # Fetch all neighbors in one DB query (max 20 to avoid giant OR clauses)
        try:
            for i in range(0, len(neighbor_filters), 20):
                batch = neighbor_filters[i : i + 20]
                where = {"$or": batch} if len(batch) > 1 else batch[0]
                
                neighbors = self.vectordb_service.get_chunks(limit=len(batch), where=where)
                
                for neighbor in neighbors:
                    # Mark as neighbor and give it a lower base score
                    neighbor["score"] = -2.0 
                    neighbor["metadata"] = neighbor.get("metadata", {})
                    neighbor["metadata"]["is_neighbor"] = True
                    expanded.append(neighbor)
                    
            logger.debug("ContextConstructor: added %d neighbor chunks", len(expanded) - len(chunks))
        except Exception as exc:
            logger.warning("ContextConstructor: failed to fetch neighbors: %s", exc)

        return expanded

    @staticmethod
    def _remove_boundary_overlap(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove the 300-char overlap between consecutive chunks."""
        
        sorted_chunks = sorted(
            chunks,
            key=lambda c: (
                c.get("metadata", {}).get("document_id", ""),
                int(c.get("metadata", {}).get("chunk_index", 0) or 0)
            )
        )

        for i in range(1, len(sorted_chunks)):
            prev = sorted_chunks[i - 1]
            curr = sorted_chunks[i]

            prev_doc = prev.get("metadata", {}).get("document_id")
            curr_doc = curr.get("metadata", {}).get("document_id")

            if prev_doc != curr_doc or not prev_doc:
                continue

            try:
                prev_idx = int(prev.get("metadata", {}).get("chunk_index", 0))
                curr_idx = int(curr.get("metadata", {}).get("chunk_index", 0))
            except (ValueError, TypeError):
                continue

            if curr_idx == prev_idx + 1:
                prev_text = prev.get("text", "")
                curr_text = curr.get("text", "")
                
                # Check the last 150 chars of prev against the first 300 chars of curr
                suffix = prev_text[-150:]
                if len(suffix) > 20:
                    idx = curr_text.find(suffix[:50])
                    if idx != -1 and idx < 300:
                        # Found overlap, trim the current chunk
                        overlap_len = len(prev_text) - prev_text.rfind(curr_text[idx:idx+50])
                        if overlap_len > 0:
                            curr["text"] = curr_text[idx + overlap_len:].strip()

        return sorted_chunks

    @staticmethod
    def _group_and_order(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Group by document, order by chunk index."""
        
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for chunk in chunks:
            doc_id = chunk.get("metadata", {}).get("document_id", "unknown")
            groups[doc_id].append(chunk)

        ordered = []
        for doc_id in sorted(groups.keys()):
            doc_chunks = sorted(
                groups[doc_id],
                key=lambda c: int(c.get("metadata", {}).get("chunk_index", 0) or 0)
            )
            ordered.extend(doc_chunks)

        return ordered

    @staticmethod
    def _enforce_budget(
        chunks: list[dict[str, Any]], max_tokens: int
    ) -> list[dict[str, Any]]:
        """Enforce maximum context token budget (1 token ~ 4 chars)."""
        
        budgeted = []
        current_chars = 0
        max_chars = max_tokens * 4

        for chunk in chunks:
            text = chunk.get("text", "")
            chars = len(text)
            
            if current_chars + chars > max_chars:
                if current_chars == 0:
                    # Truncate first chunk if it's too big
                    chunk["text"] = text[:max_chars]
                    budgeted.append(chunk)
                break
                
            budgeted.append(chunk)
            current_chars += chars

        return budgeted

    @staticmethod
    def _format_for_llm(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Add document separators for LLM clarity."""
        
        formatted = []
        current_doc = None

        for chunk in chunks:
            doc_id = chunk.get("metadata", {}).get("document_id", "")
            text = chunk.get("text", "")
            
            if doc_id != current_doc:
                current_doc = doc_id
                filename = chunk.get("metadata", {}).get("filename", doc_id)
                formatted_text = f"=== Document: {filename} ===\n\n{text}"
                
                # Create a new chunk to avoid mutating the original
                new_chunk = chunk.copy()
                new_chunk["text"] = formatted_text
                formatted.append(new_chunk)
            else:
                formatted.append(chunk)

        return formatted
