"""Defense-in-depth source filtering for INDUS MIND retrieval.

The ScopeEnforcer ensures that document_id whitelists are treated as hard
invariants — not soft preferences.  Every retrieval code path must pass
results through the enforcer before returning them to callers.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ScopeViolationError(Exception):
    """Raised when a retrieval result violates the document scope constraint."""


class ScopeEnforcer:
    """Enforce document_id whitelist constraints on retrieval results.

    Usage:
        enforcer = ScopeEnforcer(allowed_document_ids=["doc_a", "doc_b"])
        safe_results = enforcer.enforce(raw_results)
    """

    def __init__(self, allowed_document_ids: list[str] | None = None) -> None:
        self._allowed: set[str] | None = (
            set(allowed_document_ids) if allowed_document_ids else None
        )

    @property
    def is_scoped(self) -> bool:
        """Return True if a document filter is active."""
        return self._allowed is not None

    def enforce(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Drop any result whose document_id is not in the whitelist.

        If no whitelist is configured, all results pass through unchanged.

        Args:
            results: Retrieval results with ``metadata.document_id``.

        Returns:
            Filtered list containing only whitelisted results.
        """

        if self._allowed is None:
            return results

        safe: list[dict[str, Any]] = []
        violations: list[str] = []

        for result in results:
            doc_id = self._extract_document_id(result)
            if doc_id in self._allowed:
                safe.append(result)
            else:
                violations.append(doc_id or "<unknown>")

        if violations:
            logger.warning(
                "SCOPE ENFORCER: dropped %d result(s) outside allowed scope. "
                "allowed=%s violations=%s",
                len(violations),
                sorted(self._allowed),
                violations,
            )

        return safe

    def validate(self, results: list[dict[str, Any]]) -> bool:
        """Check whether all results respect the scope without filtering.

        Returns:
            True if every result is within scope (or no scope is set).
        """

        if self._allowed is None:
            return True

        for result in results:
            doc_id = self._extract_document_id(result)
            if doc_id not in self._allowed:
                return False

        return True

    @staticmethod
    def _extract_document_id(result: dict[str, Any]) -> str:
        """Extract document_id from a retrieval result dict."""
        metadata = result.get("metadata") or {}
        return str(metadata.get("document_id", "")).strip()
