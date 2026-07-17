"""Intelligent document selection for INDUS MIND retrieval.

Determines which documents should participate in retrieval based on
user-selected PDFs, extracted entities, and query intent.  Enforces
strict single-document isolation when only one PDF is selected.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.services.entity_extractor import ExtractedEntity, EntityType

logger = logging.getLogger(__name__)


class DocumentScope(str, Enum):
    """How tightly retrieval is bound to specific documents."""

    STRICT_SINGLE = "strict_single"       # Exactly one PDF — NEVER search others
    STRICT_MULTI = "strict_multi"         # Multiple PDFs — only those
    ALL = "all"                           # No filter — search everything
    ENTITY_RESOLVED = "entity_resolved"   # System resolved docs via entity registry


@dataclass
class DocumentSelection:
    """Result of the document selection decision."""

    selected_ids: list[str]
    scope: DocumentScope
    reason: str

    @property
    def is_scoped(self) -> bool:
        """True when retrieval is restricted to specific documents."""
        return self.scope != DocumentScope.ALL

    @property
    def is_strict(self) -> bool:
        """True when out-of-scope results must be completely rejected."""
        return self.scope in (DocumentScope.STRICT_SINGLE, DocumentScope.STRICT_MULTI)


class DocumentSelector:
    """Decide which documents should participate in retrieval.

    Decision priority:
    1. If the user explicitly selected documents → respect that (hard constraint)
    2. If entities map to specific documents → use those (soft preference)
    3. Otherwise → search everything

    This replaces the ad-hoc ``ScopeEnforcer`` as the single authority on
    document scope.  The enforcer is still used downstream as a safety net.
    """

    def select(
        self,
        user_selected_ids: list[str] | None,
        entities: list[ExtractedEntity],
        intent: str,
    ) -> DocumentSelection:
        """Determine which documents to include in retrieval.

        Args:
            user_selected_ids: Document IDs explicitly chosen by the user in
                the frontend PDF selection UI.  ``None`` or empty means "all".
            entities: Entities extracted from the query, possibly with
                ``source_document_ids`` populated from the entity registry.
            intent: Classified query intent string.

        Returns:
            A DocumentSelection with the final scope decision.
        """

        # ── Rule 1: User selection is authoritative ──────────────────
        if user_selected_ids:
            if len(user_selected_ids) == 1:
                logger.info(
                    "DocumentSelector: STRICT_SINGLE — user selected 1 document: %s",
                    user_selected_ids[0],
                )
                return DocumentSelection(
                    selected_ids=list(user_selected_ids),
                    scope=DocumentScope.STRICT_SINGLE,
                    reason=f"User selected 1 document: {user_selected_ids[0]}",
                )

            logger.info(
                "DocumentSelector: STRICT_MULTI — user selected %d documents",
                len(user_selected_ids),
            )
            return DocumentSelection(
                selected_ids=list(user_selected_ids),
                scope=DocumentScope.STRICT_MULTI,
                reason=f"User selected {len(user_selected_ids)} documents",
            )

        # ── Rule 2: Entity-resolved scope ────────────────────────────
        entity_doc_ids: set[str] = set()
        for entity in entities:
            # Only use entities with high confidence document associations
            if entity.source_document_ids and entity.confidence >= 0.7:
                entity_doc_ids.update(entity.source_document_ids)

        if entity_doc_ids:
            sorted_ids = sorted(entity_doc_ids)
            entity_names = [e.text for e in entities if e.source_document_ids]
            logger.info(
                "DocumentSelector: ENTITY_RESOLVED — entities %s map to %d documents: %s",
                entity_names,
                len(sorted_ids),
                sorted_ids,
            )
            return DocumentSelection(
                selected_ids=sorted_ids,
                scope=DocumentScope.ENTITY_RESOLVED,
                reason=f"Entities {entity_names} found in documents {sorted_ids}",
            )

        # ── Rule 3: Global search ────────────────────────────────────
        logger.info("DocumentSelector: ALL — no document filter applied")
        return DocumentSelection(
            selected_ids=[],
            scope=DocumentScope.ALL,
            reason="No document filter applied — searching entire knowledge base",
        )
