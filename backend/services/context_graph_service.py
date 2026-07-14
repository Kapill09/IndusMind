"""Build an answer-scoped knowledge graph from RAG response data.

This service constructs a *temporary* context graph that visualises only the
knowledge the RAG pipeline actually used to produce an answer.  It never
queries ChromaDB — it works entirely from the ``sources`` and ``entities``
already returned by ``/api/ask``.
"""

import logging
import re
from collections import defaultdict
from typing import Any

from backend.services.knowledge_graph_service import ENTITY_PATTERNS

logger = logging.getLogger(__name__)

# Compile once at import time.
_COMPILED_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (entity_type, re.compile(pattern, re.IGNORECASE))
    for entity_type, patterns in ENTITY_PATTERNS.items()
    for pattern in patterns
]

# Hard caps — keep the graph readable.
MAX_NODES = 40
MAX_EDGES = 60

# Node types that are always kept during pruning.
_PROTECTED_TYPES = {"Question", "Document", "Problem Statements"}

# Category quotas when pruning.
_CATEGORY_QUOTAS: dict[str, int] = {
    "Question": 1,
    "Document": 5,
    "Problem Statements": 4,
    "Technologies": 5,
    "Equipment": 5,
    "Standards": 4,
    "SOPs": 3,
    "Safety terms": 3,
    "Maintenance concepts": 3,
    "Regulations": 3,
}


class ContextGraphServiceError(Exception):
    """Raised when context-graph construction fails."""


class ContextGraphService:
    """Build a lightweight, answer-scoped knowledge graph."""

    def build_context_graph(
        self,
        *,
        question: str,
        sources: list[dict[str, Any]],
        entities: list[dict[str, Any]],
        answer: str,
    ) -> dict[str, Any]:
        """Return ``{nodes, edges, stats}`` for the Context Graph drawer.

        Parameters
        ----------
        question:
            The user question that triggered the RAG pipeline.
        sources:
            The ``sources`` array from the ``/api/ask`` response — each item
            has ``chunk_id``, ``text``, ``page_start``, ``page_end``,
            ``score``, and ``metadata``.
        entities:
            The ``entities`` array from ``/api/ask`` (label + type pairs).
        answer:
            The generated answer text — used for supplementary entity
            extraction when the source texts are short.
        """

        try:
            nodes_by_id: dict[str, dict[str, Any]] = {}
            edges: list[dict[str, Any]] = []

            # ── 1. Question root node ────────────────────────────────
            q_id = "question:root"
            nodes_by_id[q_id] = {
                "id": q_id,
                "label": question[:120] + ("…" if len(question) > 120 else ""),
                "type": "Question",
                "description": "User query",
                "rank": 0,
                "confidence": None,
                "page": None,
                "document": None,
                "sourceChunkId": None,
            }

            # ── 2. Document nodes (deduplicated) ─────────────────────
            doc_map: dict[str, dict[str, Any]] = {}  # document_id → best source
            for source in sources:
                meta = source.get("metadata") or {}
                doc_id = str(meta.get("document_id") or self._doc_id_from_chunk(source.get("chunk_id", "")))
                if not doc_id:
                    continue
                score = self._safe_float(source.get("score"))
                if doc_id not in doc_map or (score or 0) > (self._safe_float(doc_map[doc_id].get("score")) or 0):
                    doc_map[doc_id] = source

            for doc_id, best_source in doc_map.items():
                meta = best_source.get("metadata") or {}
                filename = str(meta.get("filename") or f"{doc_id}.pdf")
                node_id = f"document:{self._safe_id(doc_id)}"
                best_score = self._safe_float(best_source.get("score"))
                nodes_by_id[node_id] = {
                    "id": node_id,
                    "label": filename,
                    "type": "Document",
                    "description": f"Source document with relevance {round((best_score or 0.7) * 100)}%",
                    "rank": 1,
                    "confidence": best_score,
                    "page": self._safe_int(best_source.get("page_start")),
                    "document": doc_id,
                    "sourceChunkId": best_source.get("chunk_id"),
                }
                self._add_edge(edges, q_id, node_id, "answered_by", best_score or 0.85)

            # ── 3. Problem Statement nodes from metadata ─────────────
            ps_seen: set[str] = set()
            for source in sources:
                meta = source.get("metadata") or {}
                ps_num = str(meta.get("problem_statement_number") or "").strip()
                if not ps_num or ps_num in ps_seen:
                    continue
                ps_seen.add(ps_num)
                label = f"Problem Statement {ps_num}"
                node_id = f"ps:{self._safe_id(label)}"
                doc_id = str(meta.get("document_id") or "")
                doc_node_id = f"document:{self._safe_id(doc_id)}" if doc_id else None
                score = self._safe_float(source.get("score"))
                nodes_by_id[node_id] = {
                    "id": node_id,
                    "label": label,
                    "type": "Problem Statements",
                    "description": f"Problem statement extracted from source metadata",
                    "rank": 2,
                    "confidence": score,
                    "page": self._safe_int(source.get("page_start")),
                    "document": doc_id,
                    "sourceChunkId": source.get("chunk_id"),
                }
                # Connect to question
                self._add_edge(edges, q_id, node_id, "about", score or 0.9)
                # Connect to parent document
                if doc_node_id and doc_node_id in nodes_by_id:
                    self._add_edge(edges, doc_node_id, node_id, "contains", 0.85)

            # ── 4. Extract entities from source texts + answer ───────
            combined_text_parts: list[tuple[str, dict[str, Any]]] = []
            for source in sources:
                text = str(source.get("text") or "")
                if text:
                    combined_text_parts.append((text, source))

            # Also extract from the answer itself (may mention entities not
            # in the raw chunks but synthesised by the LLM).
            if answer:
                combined_text_parts.append((answer, {}))

            entity_nodes: dict[str, dict[str, Any]] = {}  # key → node
            entity_source_map: dict[str, list[str]] = defaultdict(list)  # entity key → [doc_node_ids]

            for text, source in combined_text_parts:
                meta = source.get("metadata") or {}
                doc_id = str(meta.get("document_id") or "")
                doc_node_id = f"document:{self._safe_id(doc_id)}" if doc_id else None
                score = self._safe_float(source.get("score"))

                for entity_type, compiled_pattern in _COMPILED_PATTERNS:
                    for match in compiled_pattern.finditer(text):
                        raw_label = match.group(0).strip()
                        label = raw_label.title() if raw_label.lower() in {"equipment", "machine", "system", "assembly"} else raw_label
                        # Skip very generic single-word labels
                        if label.lower() in {"procedure", "system", "machine", "assembly", "equipment"}:
                            continue
                        key = f"{entity_type}:{label.lower()}"
                        if key not in entity_nodes:
                            node_id = f"entity:{self._safe_id(key)}"
                            entity_nodes[key] = {
                                "id": node_id,
                                "label": label,
                                "type": entity_type,
                                "description": f"Extracted {entity_type.lower()} from retrieved context",
                                "rank": 3,
                                "confidence": score,
                                "page": self._safe_int(source.get("page_start") if source else None),
                                "document": doc_id,
                                "sourceChunkId": source.get("chunk_id") if source else None,
                            }
                        if doc_node_id:
                            entity_source_map[key].append(doc_node_id)

            # Also include entities from the /api/ask response (pipeline-extracted)
            for ent in entities:
                label = str(ent.get("label", "")).strip()
                etype = str(ent.get("type", "")).strip()
                if not label or not etype:
                    continue
                key = f"{etype}:{label.lower()}"
                if key not in entity_nodes:
                    node_id = f"entity:{self._safe_id(key)}"
                    entity_nodes[key] = {
                        "id": node_id,
                        "label": label,
                        "type": etype,
                        "description": f"Extracted {etype.lower()} from RAG pipeline",
                        "rank": 3,
                        "confidence": None,
                        "page": None,
                        "document": None,
                        "sourceChunkId": None,
                    }

            # ── 5. Add entity nodes & edges ──────────────────────────
            for key, enode in entity_nodes.items():
                nodes_by_id[enode["id"]] = enode
                # Connect to parent documents
                seen_docs: set[str] = set()
                for doc_nid in entity_source_map.get(key, []):
                    if doc_nid in nodes_by_id and doc_nid not in seen_docs:
                        seen_docs.add(doc_nid)
                        self._add_edge(edges, doc_nid, enode["id"], "mentions", enode.get("confidence") or 0.7)

                # Connect to problem statements if they share a document
                for ps_id, ps_node in nodes_by_id.items():
                    if ps_node["type"] == "Problem Statements" and ps_node.get("document") == enode.get("document") and enode.get("document"):
                        self._add_edge(edges, ps_id, enode["id"], "involves", 0.6)

            # ── 6. Connect related entities (same type co-occurrence) ─
            by_type: dict[str, list[str]] = defaultdict(list)
            for enode in entity_nodes.values():
                by_type[enode["type"]].append(enode["id"])
            for type_nodes in by_type.values():
                if len(type_nodes) < 2:
                    continue
                # Chain-link same-type entities (up to 6)
                for a, b in zip(type_nodes[:6], type_nodes[1:7]):
                    self._add_edge(edges, a, b, "related_to", 0.4)

            # ── 7. Heading / SOP nodes from metadata ─────────────────
            heading_seen: set[str] = set()
            for source in sources:
                meta = source.get("metadata") or {}
                heading = str(meta.get("heading") or "").strip()
                if not heading or heading.lower() in heading_seen:
                    continue
                heading_seen.add(heading.lower())
                node_id = f"sop:{self._safe_id(heading)}"
                doc_id = str(meta.get("document_id") or "")
                doc_node_id = f"document:{self._safe_id(doc_id)}" if doc_id else None
                score = self._safe_float(source.get("score"))
                nodes_by_id[node_id] = {
                    "id": node_id,
                    "label": heading,
                    "type": "SOPs",
                    "description": "Section heading from source document",
                    "rank": 2,
                    "confidence": score,
                    "page": self._safe_int(source.get("page_start")),
                    "document": doc_id,
                    "sourceChunkId": source.get("chunk_id"),
                }
                if doc_node_id and doc_node_id in nodes_by_id:
                    self._add_edge(edges, doc_node_id, node_id, "contains", 0.8)

            # ── 8. Prune if over limits ──────────────────────────────
            nodes_by_id, edges = self._prune(nodes_by_id, edges)

            # ── 9. Stats ─────────────────────────────────────────────
            type_counts: dict[str, int] = defaultdict(int)
            for n in nodes_by_id.values():
                type_counts[n["type"]] += 1

            logger.info(
                "Context graph built: question=%s nodes=%s edges=%s",
                question[:60],
                len(nodes_by_id),
                len(edges),
            )

            return {
                "nodes": list(nodes_by_id.values()),
                "edges": edges,
                "stats": {
                    "totalNodes": len(nodes_by_id),
                    "totalEdges": len(edges),
                    "entityTypes": dict(type_counts),
                },
            }

        except Exception as exc:
            logger.exception("Failed to build context graph")
            raise ContextGraphServiceError(str(exc)) from exc

    # ── Helpers ───────────────────────────────────────────────────────

    def _prune(
        self,
        nodes_by_id: dict[str, dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        """Prune the graph to stay within MAX_NODES / MAX_EDGES."""

        if len(nodes_by_id) <= MAX_NODES and len(edges) <= MAX_EDGES:
            return nodes_by_id, edges

        # Score nodes by connectivity + confidence.
        edge_counts: dict[str, int] = defaultdict(int)
        for e in edges:
            edge_counts[e["source"]] += 1
            edge_counts[e["target"]] += 1

        def node_score(n: dict[str, Any]) -> float:
            base = edge_counts.get(n["id"], 0)
            conf = n.get("confidence") or 0
            protected_bonus = 100 if n["type"] in _PROTECTED_TYPES else 0
            return base + conf + protected_bonus

        # Keep top-N per category.
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for n in nodes_by_id.values():
            by_type[n["type"]].append(n)

        kept_ids: set[str] = set()
        for ntype, group in by_type.items():
            quota = _CATEGORY_QUOTAS.get(ntype, 3)
            sorted_group = sorted(group, key=node_score, reverse=True)
            for n in sorted_group[:quota]:
                kept_ids.add(n["id"])

        # Fill remaining slots.
        remaining = [n for n in nodes_by_id.values() if n["id"] not in kept_ids]
        remaining.sort(key=node_score, reverse=True)
        for n in remaining:
            if len(kept_ids) >= MAX_NODES:
                break
            kept_ids.add(n["id"])

        pruned_nodes = {nid: nodes_by_id[nid] for nid in kept_ids}
        pruned_edges = [e for e in edges if e["source"] in kept_ids and e["target"] in kept_ids]

        # Trim edges if still over limit.
        if len(pruned_edges) > MAX_EDGES:
            pruned_edges.sort(key=lambda e: e.get("weight", 0), reverse=True)
            pruned_edges = pruned_edges[:MAX_EDGES]

        return pruned_nodes, pruned_edges

    @staticmethod
    def _add_edge(
        edges: list[dict[str, Any]],
        source: str,
        target: str,
        relationship: str,
        weight: float,
    ) -> None:
        if not source or not target or source == target:
            return
        # Deduplicate.
        for e in edges:
            if e["source"] == source and e["target"] == target and e["relationship"] == relationship:
                return
        edges.append({
            "source": source,
            "target": target,
            "relationship": relationship,
            "weight": round(weight, 2),
        })

    @staticmethod
    def _safe_id(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _doc_id_from_chunk(chunk_id: str) -> str:
        if ":chunk-" in chunk_id:
            return chunk_id.split(":chunk-", 1)[0]
        if ":" in chunk_id:
            return chunk_id.rsplit(":", 1)[0]
        return chunk_id or "unknown"
