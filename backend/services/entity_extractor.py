"""Entity extraction and resolution for INDUS MIND retrieval.

Extracts structured entities (problem statements, standards, pages) and
unstructured entities (acronyms, protocol names, technology terms) from
user queries.  Maintains a persistent entity registry built at ingestion
time that maps entity names to their source documents.
"""

import logging
import os
import pickle
import re
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import backend.config as config

logger = logging.getLogger(__name__)

_DEFAULT_REGISTRY_DIR = Path(
    getattr(config, "ENTITY_REGISTRY_PATH", "./data/entities")
)
if not _DEFAULT_REGISTRY_DIR.is_absolute():
    _DEFAULT_REGISTRY_DIR = Path(__file__).resolve().parents[2] / _DEFAULT_REGISTRY_DIR

_REGISTRY_FILE = "entity_registry.pkl"


class EntityType(str, Enum):
    """Classification of an extracted entity."""

    DOCUMENT_NAME = "document_name"
    PROBLEM_STATEMENT = "problem_statement"
    MACHINE = "machine"
    STANDARD = "standard"
    TECHNOLOGY = "technology"
    ALGORITHM = "algorithm"
    PERSON = "person"
    ABBREVIATION = "abbreviation"
    PROTOCOL = "protocol"
    SECTION = "section"
    PAGE = "page"
    CHAPTER = "chapter"
    FIGURE = "figure"
    TABLE = "table"


@dataclass
class ExtractedEntity:
    """One entity extracted from a user query."""

    text: str
    entity_type: EntityType
    normalized: str
    source_document_ids: list[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class EntityRegistryEntry:
    """An entity known to exist in the indexed document corpus."""

    text: str
    entity_type: EntityType
    normalized: str
    document_ids: set[str] = field(default_factory=set)
    frequency: int = 0


class EntityExtractor:
    """Extract and resolve entities from user queries.

    Combines three extraction layers:
    1. Regex patterns for structured references (problem statements, pages, etc.)
    2. Registry lookup against entities discovered during document ingestion
    3. Acronym/capitalized-term detection for unknown entities

    Args:
        registry_dir: Directory for persisting the entity registry.
    """

    _STRUCTURED_PATTERNS: tuple[tuple[EntityType, re.Pattern[str]], ...] = (
        (
            EntityType.PROBLEM_STATEMENT,
            re.compile(
                r"\bproblem\s+(?:(?:statement|stmt|statemtn|statment)\s*)?(?:number|no\.?|#)?\s*([A-Za-z]?\d+[A-Za-z]?)\b",
                re.IGNORECASE,
            ),
        ),
        (
            EntityType.SECTION,
            re.compile(
                r"\bsection\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b",
                re.IGNORECASE,
            ),
        ),
        (
            EntityType.CHAPTER,
            re.compile(
                r"\bchapter\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b",
                re.IGNORECASE,
            ),
        ),
        (
            EntityType.PAGE,
            re.compile(r"\bpage\s*(?:number|no\.?|#)?\s*(\d+)\b", re.IGNORECASE),
        ),
        (
            EntityType.FIGURE,
            re.compile(
                r"\b(?:figure|fig\.?)\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b",
                re.IGNORECASE,
            ),
        ),
        (
            EntityType.TABLE,
            re.compile(
                r"\btable\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b",
                re.IGNORECASE,
            ),
        ),
        (
            EntityType.STANDARD,
            re.compile(
                r"\b((?:ISO|IEC|API|ANSI|ASTM|OSHA|NFPA|IEEE)\s*[\d][\d./-]*)\b",
                re.IGNORECASE,
            ),
        ),
    )

    # Words that look like acronyms but are common English or query fragments.
    _ACRONYM_STOPWORDS: frozenset[str] = frozenset({
        "AI", "ML", "IT", "OR", "AN", "IF", "IS", "AS", "AT", "BY",
        "DO", "GO", "IN", "NO", "OF", "ON", "SO", "TO", "UP", "US",
        "WE", "BE", "HE", "ME", "MY", "OK", "OUR", "THE", "AND",
        "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER", "WAS",
        "ONE", "HOW", "HAS", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE",
        "WAY", "WHO", "DID", "GET", "HIM", "HIS", "LET", "SAY", "SHE",
        "TOO", "USE", "WHAT", "WHEN", "WHERE", "WHICH", "WHY", "WILL",
        "WITH", "COMPARE", "BETWEEN", "EXPLAIN", "DESCRIBE", "ABOUT",
        "GIVE", "LIST", "SHOW", "FIND", "TELL", "KNOW", "DOES",
        "DEFINE", "SUMMARIZE", "SUMMARISE", "OPEN", "PROPOSED",
        "PROBLEM", "STATEMENT", "PAPER",
        "PDF", "RAG", "LLM",
    })

    _ACRONYM_RE = re.compile(r"\b([A-Z][A-Z0-9]{1,}(?:[a-z][A-Za-z0-9]*)?)\b")

    # Technology terms detected by pattern.
    _TECHNOLOGY_RE = re.compile(
        r"\b(IoT|IoD|SCADA|PLC|DCS|HMI|OPC|MQTT|BACnet|Modbus|ERP|MES|CMMS|CNC|PID|VFD|RTU)\b",
        re.IGNORECASE,
    )

    def __init__(self, *, registry_dir: Path | str = _DEFAULT_REGISTRY_DIR) -> None:
        self._registry_dir = Path(registry_dir)
        self._registry_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self._registry_dir / _REGISTRY_FILE
        self._lock = threading.Lock()
        self._registry: dict[str, EntityRegistryEntry] = {}
        self._load_registry()

    # ── Public API ────────────────────────────────────────────────────

    def extract(self, query: str) -> list[ExtractedEntity]:
        """Extract entities from a user query using all three layers.

        Returns entities ordered by confidence (highest first).
        """

        entities: list[ExtractedEntity] = []

        # Layer 1: Structured regex patterns (highest confidence)
        entities.extend(self._regex_extract(query))

        # Layer 2: Registry lookup (high confidence — known entities)
        entities.extend(self._registry_lookup(query))

        # Layer 3: Acronym / capitalized-term detection (medium confidence)
        entities.extend(self._acronym_detection(query))

        # Layer 4: Technology patterns
        entities.extend(self._technology_detection(query))

        deduped = self._deduplicate(entities)
        deduped.sort(key=lambda e: e.confidence, reverse=True)
        return deduped

    def build_registry(self, document_id: str, chunks: list[dict[str, Any]]) -> int:
        """Extract entities from ingested chunks and add them to the registry.

        Called at ingestion time. Scans chunk text for acronyms, capitalized
        technical terms, and structured metadata to build a mapping from
        entity names to their source documents.

        Returns:
            Number of new entity entries added.
        """

        new_entries = 0

        with self._lock:
            for chunk in chunks:
                text = str(chunk.get("text", ""))
                metadata = chunk.get("metadata", {})

                # Extract from structured metadata
                for meta_key, entity_type in (
                    ("problem_statement_number", EntityType.PROBLEM_STATEMENT),
                    ("section_number", EntityType.SECTION),
                    ("chapter_number", EntityType.CHAPTER),
                    ("heading", EntityType.ABBREVIATION),
                ):
                    value = metadata.get(meta_key)
                    if value and str(value).strip():
                        new_entries += self._register_entity(
                            str(value).strip(), entity_type, document_id
                        )

                # Extract acronyms from text
                for match in self._ACRONYM_RE.finditer(text):
                    term = match.group(1)
                    if term not in self._ACRONYM_STOPWORDS and len(term) >= 2:
                        new_entries += self._register_entity(
                            term, EntityType.ABBREVIATION, document_id
                        )

                # Extract technology terms
                for match in self._TECHNOLOGY_RE.finditer(text):
                    term = match.group(1)
                    new_entries += self._register_entity(
                        term, EntityType.TECHNOLOGY, document_id
                    )

            self._persist_registry()

        logger.info(
            "Entity registry updated: document_id=%s new_entries=%d total=%d",
            document_id,
            new_entries,
            len(self._registry),
        )
        return new_entries

    def remove_document(self, document_id: str) -> int:
        """Remove all entity references for a document from the registry."""

        removed = 0
        with self._lock:
            to_delete: list[str] = []
            for key, entry in self._registry.items():
                if document_id in entry.document_ids:
                    entry.document_ids.discard(document_id)
                    removed += 1
                    if not entry.document_ids:
                        to_delete.append(key)

            for key in to_delete:
                del self._registry[key]

            self._persist_registry()

        logger.info(
            "Entity registry cleaned: document_id=%s removed=%d remaining=%d",
            document_id,
            removed,
            len(self._registry),
        )
        return removed

    @property
    def registry_size(self) -> int:
        """Number of unique entities in the registry."""
        return len(self._registry)

    # ── Extraction Layers ─────────────────────────────────────────────

    def _regex_extract(self, query: str) -> list[ExtractedEntity]:
        """Layer 1: Extract structured entities via regex patterns."""

        entities: list[ExtractedEntity] = []
        for entity_type, pattern in self._STRUCTURED_PATTERNS:
            for match in pattern.finditer(query):
                text = match.group(0).strip()
                identifier = match.group(1).strip()
                entities.append(
                    ExtractedEntity(
                        text=text,
                        entity_type=entity_type,
                        normalized=identifier.lower(),
                        source_document_ids=[],
                        confidence=1.0,
                    )
                )
        return entities

    def _registry_lookup(self, query: str) -> list[ExtractedEntity]:
        """Layer 2: Match query tokens against the entity registry."""

        entities: list[ExtractedEntity] = []
        query_lower = query.lower()
        query_tokens = set(re.findall(r"[a-z0-9]+", query_lower))

        for key, entry in self._registry.items():
            # Match by exact token or substring
            entry_lower = entry.text.lower()
            if not self._is_valid_registry_candidate(entry.text):
                continue

            exact_phrase = re.search(
                rf"(?<![A-Za-z0-9]){re.escape(entry_lower)}(?![A-Za-z0-9])",
                query_lower,
            )
            if exact_phrase or entry.normalized in query_tokens:
                entities.append(
                    ExtractedEntity(
                        text=entry.text,
                        entity_type=entry.entity_type,
                        normalized=entry.normalized,
                        source_document_ids=sorted(entry.document_ids),
                        confidence=0.9,
                    )
                )

        return entities

    @classmethod
    def _is_valid_registry_candidate(cls, text: str) -> bool:
        clean = text.strip()
        if len(clean) < 2 and not clean.isdigit():
            return False
        if clean.upper() in cls._ACRONYM_STOPWORDS:
            return False
        return True

    def _acronym_detection(self, query: str) -> list[ExtractedEntity]:
        """Layer 3: Detect capitalized terms as potential entity names."""

        entities: list[ExtractedEntity] = []
        for match in self._ACRONYM_RE.finditer(query):
            term = match.group(1)
            if term in self._ACRONYM_STOPWORDS:
                continue
            if len(term) < 2:
                continue

            # Check if it's already captured by registry or regex
            normalized = term.lower()

            # Look up in registry for document association
            registry_entry = self._registry.get(normalized)
            doc_ids = sorted(registry_entry.document_ids) if registry_entry else []

            entities.append(
                ExtractedEntity(
                    text=term,
                    entity_type=EntityType.ABBREVIATION,
                    normalized=normalized,
                    source_document_ids=doc_ids,
                    confidence=0.7 if doc_ids else 0.5,
                )
            )

        return entities

    def _technology_detection(self, query: str) -> list[ExtractedEntity]:
        """Layer 4: Detect known technology terms."""

        entities: list[ExtractedEntity] = []
        for match in self._TECHNOLOGY_RE.finditer(query):
            term = match.group(1)
            normalized = term.lower()
            registry_entry = self._registry.get(normalized)
            doc_ids = sorted(registry_entry.document_ids) if registry_entry else []

            entities.append(
                ExtractedEntity(
                    text=term,
                    entity_type=EntityType.TECHNOLOGY,
                    normalized=normalized,
                    source_document_ids=doc_ids,
                    confidence=0.85,
                )
            )

        return entities

    # ── Internal Helpers ──────────────────────────────────────────────

    def _register_entity(
        self, text: str, entity_type: EntityType, document_id: str
    ) -> int:
        """Register or update an entity in the registry. Returns 1 if new, 0 if updated."""

        normalized = text.strip().lower()
        if not normalized:
            return 0

        key = normalized
        if key in self._registry:
            entry = self._registry[key]
            entry.document_ids.add(document_id)
            entry.frequency += 1
            return 0

        self._registry[key] = EntityRegistryEntry(
            text=text,
            entity_type=entity_type,
            normalized=normalized,
            document_ids={document_id},
            frequency=1,
        )
        return 1

    @staticmethod
    def _deduplicate(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
        """Remove duplicate entities, keeping the highest-confidence version."""

        seen: dict[str, ExtractedEntity] = {}
        for entity in entities:
            key = entity.normalized
            existing = seen.get(key)
            if existing is None or entity.confidence > existing.confidence:
                # Merge document IDs
                if existing:
                    merged_docs = sorted(
                        set(existing.source_document_ids) | set(entity.source_document_ids)
                    )
                    entity = ExtractedEntity(
                        text=entity.text,
                        entity_type=entity.entity_type,
                        normalized=entity.normalized,
                        source_document_ids=merged_docs,
                        confidence=entity.confidence,
                    )
                seen[key] = entity

        return list(seen.values())

    def _persist_registry(self) -> None:
        """Serialize the entity registry to disk."""
        try:
            with open(self._registry_path, "wb") as f:
                pickle.dump(self._registry, f)
        except Exception:
            logger.exception("Failed to persist entity registry to %s", self._registry_path)

    def _load_registry(self) -> None:
        """Load a previously persisted entity registry."""
        if not self._registry_path.exists():
            logger.info("No existing entity registry found at %s", self._registry_path)
            return

        try:
            with open(self._registry_path, "rb") as f:
                self._registry = pickle.load(f)
            logger.info("Entity registry loaded: entries=%d", len(self._registry))
        except Exception:
            logger.exception("Failed to load entity registry from %s", self._registry_path)
            self._registry = {}
