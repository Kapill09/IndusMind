import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from backend.services.document_service import DocumentService

logger = logging.getLogger(__name__)

ENTITY_PATTERNS = {
    "Equipment": [
        r"\b(pump|compressor|valve|motor|gearbox|turbine|reactor|boiler|conveyor|generator|sensor|controller|actuator|vessel|pipeline|drill|engine)\b",
        r"\b(equipment|machine|system|assembly)\b",
    ],
    "Problem Statements": [
        r"\b(problem statement|ps\s*\d+|problem\s*no\.?\s*\d+)\b",
        r"\b(issue|fault|failure|breakdown|malfunction|defect)\b",
    ],
    "SOPs": [
        r"\b(sop|standard operating procedure|procedure|work instruction)\b",
    ],
    "Technologies": [
        r"\b(iot|ai|ml|predictive maintenance|condition monitoring|digital twin|scada|plc|robotics|automation)\b",
    ],
    "Safety terms": [
        r"\b(safety|hazard|risk|lockout|tagout|ppe|incident|accident|emergency)\b",
    ],
    "Standards": [
        r"\b(iso|iec|api|ansi|astm|osha|nfpa|ieee)\b",
    ],
    "Regulations": [
        r"\b(regulation|compliance|regulatory|code|permit|license)\b",
    ],
    "Maintenance concepts": [
        r"\b(maintenance|inspection|lubrication|calibration|overhaul|repair|downtime|preventive|predictive)\b",
    ],
}


class KnowledgeGraphServiceError(Exception):
    """Base exception for knowledge graph service errors."""


class KnowledgeGraphService:
    """Build a lightweight knowledge graph from indexed document chunks."""

    def __init__(self, document_service: DocumentService | None = None) -> None:
        self.document_service = document_service or DocumentService()
        self.compiled_entity_patterns = self._compile_entity_patterns()

    def build_graph(self, document_ids: list[str] | None = None) -> dict[str, list[dict[str, Any]]]:
        """Construct a JSON graph with nodes and edges derived from indexed chunks."""

        try:
            where = None
            if document_ids:
                where = {"document_id": {"$in": document_ids}}
            chunks = self.document_service.vectordb_service.get_chunks(where=where)
        except Exception as exc:
            logger.exception("Failed to read chunks for knowledge graph")
            raise KnowledgeGraphServiceError("Unable to read vector chunks for knowledge graph construction.") from exc

        if not chunks:
            logger.warning(
                "Knowledge graph source loaded no Chroma chunks: collection=%s",
                self.document_service.vectordb_service.collection_name,
            )
            return {"nodes": [], "edges": []}

        nodes_by_id: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        node_index: dict[tuple[str, str], str] = {}

        logger.info(
            "Knowledge graph source loaded from Chroma: collection=%s chunks=%s",
            self.document_service.vectordb_service.collection_name,
            len(chunks),
        )

        for chunk in chunks:
            metadata = chunk.get("metadata") or {}
            chunk_id = self._resolve_chunk_id(chunk)
            document_id = self._resolve_document_id(chunk_id, metadata)
            filename = self._resolve_filename(chunk_id, metadata, document_id)
            page = self._clean_page(metadata.get("page_start"))
            text = self._clean_string(chunk.get("text"))

            if not chunk_id:
                logger.warning("Skipping Chroma record without a resolvable chunk_id: metadata=%s", metadata)
                continue

            self._ensure_node(
                nodes_by_id,
                node_index,
                node_type="Document",
                identifier=document_id,
                label=filename,
                page=None,
                document=document_id,
                description="Indexed source document from ChromaDB",
            )

            chunk_label = f"Chunk {metadata.get('chunk_index') or chunk_id.rsplit(':', 1)[-1]}"
            self._ensure_node(
                nodes_by_id,
                node_index,
                node_type="Chunk",
                identifier=chunk_id,
                label=chunk_label,
                page=page,
                document=document_id,
                description=(text[:180] + "...") if len(text) > 180 else text,
            )

            document_node_id = node_index[("document", document_id)]
            chunk_node_id = node_index[("chunk", chunk_id)]
            self._add_edge(edges, document_node_id, chunk_node_id, "contains", 1.0)

            entity_nodes = self._extract_entities(text, metadata, document_id, page)
            for entity_node in entity_nodes:
                self._upsert_node(nodes_by_id, node_index, entity_node)
                self._add_edge(edges, chunk_node_id, entity_node["id"], "mentions", 0.9)
                self._add_edge(edges, document_node_id, entity_node["id"], "mentions", 0.6)

            if page is not None:
                self._ensure_node(
                    nodes_by_id,
                    node_index,
                    node_type="Page",
                    identifier=f"{document_id}:{page}",
                    label=f"Page {page}",
                    page=page,
                    document=document_id,
                    description="Page-level knowledge context",
                )
                page_node_id = node_index[("page", f"{document_id}:{page}")]
                self._add_edge(edges, document_node_id, page_node_id, "references", 0.85)
                self._add_edge(edges, page_node_id, chunk_node_id, "contains", 0.75)

        self._connect_related_entities(nodes_by_id, edges)
        self._refresh_document_descriptions(nodes_by_id)

        logger.info(
            "Knowledge graph built from Chroma: nodes=%s edges=%s",
            len(nodes_by_id),
            len(edges),
        )
        return {
            "nodes": list(nodes_by_id.values()),
            "edges": edges,
        }

    def _extract_entities(self, text: str, metadata: dict[str, Any], document_id: str, page: Any) -> list[dict[str, Any]]:
        """Extract typed entities from text and metadata using heuristic patterns."""

        entities: list[dict[str, Any]] = []
        labels: set[str] = set()

        for entity_type, patterns in self.compiled_entity_patterns.items():
            for compiled_pattern in patterns:
                matches = compiled_pattern.finditer(text)
                for match in matches:
                    label = match.group(0).strip()
                    if label.lower() in {"equipment", "machine", "system", "assembly"}:
                        label = label.title()
                    if label in labels:
                        continue
                    labels.add(label)
                    entity_id = self._make_node_id(entity_type.lower().replace(" ", "_"), f"{document_id}:{label}:{page}")
                    entities.append(
                        {
                            "id": entity_id,
                            "label": label,
                            "type": entity_type,
                            "page": page,
                            "document": document_id,
                            "description": f"Extracted {entity_type.lower()} reference from the indexed document.",
                        }
                    )

        problem_statement_number = self._clean_string(metadata.get("problem_statement_number"))
        if problem_statement_number:
            label = f"Problem Statement {problem_statement_number}"
            entity_id = self._make_node_id("problem_statement", f"{document_id}:{label}")
            entities.append(
                {
                    "id": entity_id,
                    "label": label,
                    "type": "Problem Statements",
                    "page": page,
                    "document": document_id,
                    "description": "Problem statement reference from document metadata.",
                }
            )

        heading = self._clean_string(metadata.get("heading"))
        if heading:
            label = heading
            entity_id = self._make_node_id("heading", f"{document_id}:{label}")
            entities.append(
                {
                    "id": entity_id,
                    "label": label,
                    "type": "SOPs",
                    "page": page,
                    "document": document_id,
                    "description": "Heading or section reference extracted from metadata.",
                }
            )

        return entities

    def _compile_entity_patterns(self) -> dict[str, list[re.Pattern[str]]]:
        """Compile every entity regex during initialization and fail early on invalid patterns."""

        compiled_patterns: dict[str, list[re.Pattern[str]]] = {}
        for entity_type, patterns in ENTITY_PATTERNS.items():
            compiled_collection: list[re.Pattern[str]] = []
            for pattern in patterns:
                try:
                    compiled_collection.append(re.compile(pattern, flags=re.IGNORECASE))
                except re.error as exc:
                    raise KnowledgeGraphServiceError(
                        f"Invalid knowledge graph regex for '{entity_type}': {pattern}"
                    ) from exc
            compiled_patterns[entity_type] = compiled_collection

        return compiled_patterns

    def _connect_related_entities(self, nodes_by_id: dict[str, dict[str, Any]], edges: list[dict[str, Any]]) -> None:
        """Link entities that share the same document or type to support graph exploration."""

        chunks_by_document: dict[str, list[str]] = defaultdict(list)
        by_type: dict[str, list[str]] = defaultdict(list)

        for node_id, node in nodes_by_id.items():
            document = node.get("document")
            if document and node.get("type") == "Chunk":
                chunks_by_document[document].append(node_id)
            node_type = node.get("type")
            if node_type and node_type not in {"Document", "Page", "Chunk"}:
                by_type[node_type].append(node_id)

        for node_ids in chunks_by_document.values():
            for source_id, target_id in zip(node_ids, node_ids[1:]):
                self._add_edge(edges, source_id, target_id, "next_chunk", 0.5)

        for node_type, node_ids in by_type.items():
            if len(node_ids) < 2:
                continue
            capped_node_ids = node_ids[:25]
            for source_id, target_id in zip(capped_node_ids, capped_node_ids[1:]):
                self._add_edge(edges, source_id, target_id, "related_to", 0.4)

    def _upsert_node(self, nodes_by_id: dict[str, dict[str, Any]], node_index: dict[tuple[str, str], str], node: dict[str, Any]) -> None:
        """Insert or update a node in the graph."""

        node_id = node["id"]
        if node_id not in nodes_by_id:
            nodes_by_id[node_id] = node
            node_index[(node["type"].lower(), node["label"])] = node_id
        else:
            existing = nodes_by_id[node_id]
            if not existing.get("description") and node.get("description"):
                existing["description"] = node["description"]

    def _ensure_node(
        self,
        nodes_by_id: dict[str, dict[str, Any]],
        node_index: dict[tuple[str, str], str],
        *,
        node_type: str,
        identifier: str,
        label: str,
        page: Any,
        document: str,
        description: str,
    ) -> None:
        """Ensure a node exists before linking it to an edge."""

        node_id = self._make_node_id(node_type.lower().replace(" ", "_"), identifier)
        if node_id not in nodes_by_id:
            nodes_by_id[node_id] = {
                "id": node_id,
                "label": label,
                "type": node_type,
                "page": page,
                "document": document,
                "description": description,
            }
        node_index[(node_type.lower().replace(" ", "_"), identifier)] = node_id

    def _add_edge(self, edges: list[dict[str, Any]], source_id: str | None, target_id: str | None, relationship: str, weight: float) -> None:
        """Add a unique edge to the graph."""

        if not source_id or not target_id or source_id == target_id:
            return

        if any(edge.get("source") == source_id and edge.get("target") == target_id and edge.get("relationship") == relationship for edge in edges):
            return

        edges.append({
            "source": source_id,
            "target": target_id,
            "relationship": relationship,
            "weight": round(weight, 2),
        })

    @staticmethod
    def _make_node_id(node_type: str, identifier: str) -> str:
        """Generate a stable node id from a node type and identifier."""

        safe_identifier = re.sub(r"[^a-zA-Z0-9]+", "_", str(identifier).strip()).strip("_")
        safe_type = re.sub(r"[^a-zA-Z0-9]+", "_", str(node_type).strip()).strip("_")
        return f"{safe_type}:{safe_identifier}".lower()

    @staticmethod
    def _clean_string(value: Any) -> str:
        """Return a stripped string for optional Chroma metadata values."""

        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _clean_page(value: Any) -> int | None:
        """Return a usable page number when metadata contains one."""

        try:
            page = int(value)
        except (TypeError, ValueError):
            return None
        return page if page >= 0 else None

    @staticmethod
    def _resolve_chunk_id(chunk: dict[str, Any]) -> str:
        """Resolve a stable chunk id from Chroma id or metadata."""

        metadata = chunk.get("metadata") or {}
        return (
            KnowledgeGraphService._clean_string(chunk.get("chunk_id"))
            or KnowledgeGraphService._clean_string(metadata.get("chunk_id"))
        )

    @staticmethod
    def _resolve_document_id(chunk_id: str, metadata: dict[str, Any]) -> str:
        """Resolve document id without dropping chunks that have older metadata."""

        document_id = KnowledgeGraphService._clean_string(metadata.get("document_id"))
        if document_id:
            return document_id

        filename = KnowledgeGraphService._clean_string(metadata.get("filename"))
        if filename:
            return Path(filename).stem

        if ":chunk-" in chunk_id:
            return chunk_id.split(":chunk-", 1)[0]

        if chunk_id:
            return chunk_id.rsplit(":", 1)[0]

        return "unknown-document"

    @staticmethod
    def _resolve_filename(chunk_id: str, metadata: dict[str, Any], document_id: str) -> str:
        """Resolve a readable document label from metadata or chunk id."""

        filename = KnowledgeGraphService._clean_string(metadata.get("filename"))
        if filename:
            return filename

        inferred = KnowledgeGraphService._filename_from_chunk_id(chunk_id)
        if inferred != "unknown.pdf":
            return inferred

        return f"{document_id}.pdf" if document_id else "unknown.pdf"

    @staticmethod
    def _filename_from_chunk_id(chunk_id: str) -> str:
        """Infer a readable source label when filename metadata is missing."""

        if not chunk_id:
            return "unknown.pdf"
        document_part = chunk_id.split(":chunk-", 1)[0]
        return Path(document_part).name or "unknown.pdf"

    @staticmethod
    def _refresh_document_descriptions(nodes_by_id: dict[str, dict[str, Any]]) -> None:
        """Update document node descriptions with actual chunk counts."""

        chunk_counts: dict[str, int] = defaultdict(int)
        for node in nodes_by_id.values():
            if node.get("type") == "Chunk":
                document = KnowledgeGraphService._clean_string(node.get("document"))
                if document:
                    chunk_counts[document] += 1

        for node in nodes_by_id.values():
            if node.get("type") != "Document":
                continue
            document = KnowledgeGraphService._clean_string(node.get("document"))
            count = chunk_counts.get(document, 0)
            node["description"] = f"Indexed source document from ChromaDB with {count} chunks."
