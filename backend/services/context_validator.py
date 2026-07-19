"""Context validation for INDUS MIND retrieval.

Validates that retrieved context actually contains the answer before sending
it to the LLM. Prevents hallucination by rejecting queries with insufficient
evidence.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.services.entity_extractor import EntityType
from backend.services.query_understanding import QueryIntent, QueryPlan

logger = logging.getLogger(__name__)


class ValidationVerdict(str, Enum):
    """Result of context validation."""

    PASS = "pass"        # Good evidence, send to LLM normally
    PARTIAL = "partial"  # Missing some entities, send to LLM with warning
    FAIL = "fail"        # Garbage results, reject without calling LLM


@dataclass
class ContextValidation:
    """Validation report."""

    verdict: ValidationVerdict
    coverage_score: float
    relevance_scores: list[float]
    entity_coverage: dict[str, bool] = field(default_factory=dict)
    missing_entities: list[str] = field(default_factory=list)
    reason: str = ""


class ContextValidator:
    """Validate retrieved chunks against the QueryPlan."""

    # Min cross-encoder score to consider a chunk "relevant"
    _MIN_RERANK_SCORE = -2.0

    def validate(
        self, query_plan: QueryPlan, chunks: list[dict[str, Any]]
    ) -> ContextValidation:
        """Validate that retrieved context can answer the question.

        Args:
            query_plan: The plan that drove retrieval.
            chunks: The final constructed context chunks.

        Returns:
            A ContextValidation report containing the verdict.
        """

        # ── Check 1: Empty context ──────────────────────────────────────
        if not chunks:
            return ContextValidation(
                verdict=ValidationVerdict.FAIL,
                coverage_score=0.0,
                relevance_scores=[],
                missing_entities=[e.text for e in query_plan.entities],
                reason="No chunks retrieved from the knowledge base.",
            )

        # ── Check 2: Relevance scores ───────────────────────────────────
        # Note: neighbors might have artificial scores, so filter them out
        # if actual scored chunks exist.
        scored_chunks = [c for c in chunks if not c.get("metadata", {}).get("is_neighbor")]
        if not scored_chunks:
            scored_chunks = chunks

        relevance_scores = [c.get("score", 0.0) for c in scored_chunks]
        best_score = max(relevance_scores) if relevance_scores else 0.0

        # If the best score is very low, the results are likely garbage
        # (Exception: structured metadata lookups bypass embedding scores)
        if not query_plan.is_structured and best_score < self._MIN_RERANK_SCORE:
            return ContextValidation(
                verdict=ValidationVerdict.FAIL,
                coverage_score=0.1,
                relevance_scores=relevance_scores,
                reason=f"Retrieved context has very low relevance (best score {best_score:.2f}).",
            )

        # ── Check 3: Entity coverage for comparisons ─────────────────────
        if query_plan.is_comparison:
            return self._validate_comparison(query_plan, chunks, relevance_scores)

        # ── Check 4: Structured lookup validation ────────────────────────
        if query_plan.is_structured:
            return self._validate_structured(query_plan, chunks, relevance_scores)

        # ── Default: Pass ────────────────────────────────────────────────
        avg_score = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        # Normalize cross-encoder scores roughly to [0, 1]
        coverage = min(1.0, max(0.1, (avg_score + 5) / 10))

        return ContextValidation(
            verdict=ValidationVerdict.PASS,
            coverage_score=coverage,
            relevance_scores=relevance_scores,
            reason="Context validated successfully.",
        )

    def _validate_comparison(
        self,
        query_plan: QueryPlan,
        chunks: list[dict[str, Any]],
        scores: list[float],
    ) -> ContextValidation:
        """Ensure both entities in a comparison are represented."""
        
        entities = query_plan.comparison_entities
        if len(entities) < 2:
            return ContextValidation(
                verdict=ValidationVerdict.PASS,
                coverage_score=0.8,
                relevance_scores=scores,
                reason="Context validated successfully.",
            )

        all_text = " ".join(c.get("text", "") for c in chunks).lower()
        
        entity_coverage = {}
        missing = []
        for entity in entities:
            found = entity.text.lower() in all_text or entity.normalized in all_text
            entity_coverage[entity.text] = found
            if not found:
                missing.append(entity.text)

        if not missing:
            return ContextValidation(
                verdict=ValidationVerdict.PASS,
                coverage_score=0.9,
                relevance_scores=scores,
                entity_coverage=entity_coverage,
                reason="Both comparison entities found in context.",
            )
            
        if len(missing) == len(entities):
            return ContextValidation(
                verdict=ValidationVerdict.FAIL,
                coverage_score=0.2,
                relevance_scores=scores,
                entity_coverage=entity_coverage,
                missing_entities=missing,
                reason=f"None of the comparison entities ({', '.join(missing)}) were found in the context.",
            )

        return ContextValidation(
            verdict=ValidationVerdict.PARTIAL,
            coverage_score=0.5,
            relevance_scores=scores,
            entity_coverage=entity_coverage,
            missing_entities=missing,
            reason=f"Missing context for entity: {missing[0]}",
        )

    def _validate_structured(
        self,
        query_plan: QueryPlan,
        chunks: list[dict[str, Any]],
        scores: list[float],
    ) -> ContextValidation:
        """Ensure the exact requested structured item was found."""
        
        if query_plan.intent in (QueryIntent.STRUCTURAL_LOOKUP, QueryIntent.PROBLEM_SOLUTION_MAPPING):
            ps_entities = [
                e for e in query_plan.entities if e.entity_type == EntityType.PROBLEM_STATEMENT
            ]
            
            for ps in ps_entities:
                found = False
                for c in chunks:
                    meta_val = str(c.get("metadata", {}).get("problem_statement_number", "")).strip()
                    text_val = str(c.get("text", "")).lower()
                    if meta_val == ps.normalized:
                        found = True
                        break
                    if ps.text.lower() in text_val or f"statement {ps.normalized}" in text_val or f"stmt {ps.normalized}" in text_val:
                        found = True
                        break
                if not found:
                    return ContextValidation(
                        verdict=ValidationVerdict.FAIL,
                        coverage_score=0.1,
                        relevance_scores=scores,
                        entity_coverage={ps.text: False},
                        missing_entities=[ps.text],
                        reason=f"Problem Statement {ps.normalized} not found in retrieved chunks.",
                    )

        # If it passes or isn't a PS lookup, it's valid
        return ContextValidation(
            verdict=ValidationVerdict.PASS,
            coverage_score=1.0,  # Structured match is authoritative
            relevance_scores=scores,
            reason="Structured entity found.",
        )
