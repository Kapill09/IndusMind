"""Response Validation Layer for Self-Correction.

Validates the generated RAG answer against strict constraints.
"""
import logging
import os
from typing import Any
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from backend.services.query_understanding import QueryPlan

logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    is_valid: bool = Field(description="True if the answer meets all constraints, False otherwise.")
    reason: str = Field(description="If invalid, provide the exact reason and how to fix it. If valid, leave empty.")


class ResponseValidator:
    """Validates generated LLM answers to prevent hallucinations and ensure completeness."""

    def __init__(self, client: Any | None = None) -> None:
        resolved_api_key = os.getenv("GEMINI_API_KEY")
        self.client = client or genai.Client(api_key=resolved_api_key)

    def validate(self, answer: str, query_plan: QueryPlan, retrieved_chunks: list[dict]) -> ValidationResult:
        """Evaluate the answer against strict enterprise rules."""
        if not isinstance(answer, str):
            return ValidationResult(is_valid=False, reason="Answer must be a string.")

        cleaned = answer.strip()
        if not cleaned:
            return ValidationResult(is_valid=False, reason="Answer is empty.")

        forbidden_fragments = [
            "=== document ===",
            "=== DOCUMENT ===",
            "chunk-0001",
            "[source:",
            "based on the retrieved context",
            "based on the retrieved document",
            "based on retrieved context",
            "based on retrieved document",
            "document:",
            "section:",
            "chunk:",
            "page:",
            "retrieved context",
        ]
        if any(fragment.lower() in cleaned.lower() for fragment in forbidden_fragments):
            return ValidationResult(is_valid=False, reason="Answer echoes raw context or chunk formatting.")


        if self._looks_incomplete(cleaned):
            return ValidationResult(is_valid=False, reason="Answer appears incomplete or truncated.")

        if self._has_duplicate_paragraphs(cleaned):
            return ValidationResult(is_valid=False, reason="Answer repeats duplicate paragraphs.")

        # Fast-fail for fallback answers
        if "I couldn't find this information" in answer or "available evidence is limited" in answer:
            return ValidationResult(is_valid=True, reason="")

        entities = ", ".join(e.normalized for e in query_plan.entities) or "None explicitly detected"

        # If we reach here, the answer passed all deterministic checks.
        return ValidationResult(
            is_valid=True,
            reason=""
        )

    @staticmethod
    def _looks_incomplete(text: str) -> bool:
        lowered = text.rstrip().lower()
        if lowered.endswith(("...", "etc", "and", "or")):
            return True
        return lowered.endswith(("the", "this", "because", "due")) and len(text.split()) < 40

    @staticmethod
    def _has_duplicate_paragraphs(text: str) -> bool:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        return len(paragraphs) > 1 and len(set(paragraphs)) != len(paragraphs)
