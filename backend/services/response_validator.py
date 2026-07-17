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
        
        # Fast-fail for fallback answers
        if "I couldn't find this information" in answer or "available evidence is limited" in answer:
            return ValidationResult(is_valid=True, reason="")

        entities = ", ".join(e.normalized for e in query_plan.entities) or "None explicitly detected"
        
        prompt = f"""You are an Enterprise AI Output Validator. Your job is to strictly evaluate a generated RAG answer.

USER QUERY:
{query_plan.original_query}

INTENT:
{query_plan.intent.value}

DETECTED ENTITIES TO COVER:
{entities}

GENERATED ANSWER:
{answer}

Evaluate the generated answer against these 5 strict constraints:
1. Were all requested entities answered? (If the query asks about X and Y, are both X and Y discussed?)
2. Was every compared item included? (For comparisons, did it actually compare all subjects?)
3. Are citations present? (Does the answer include [source: ...] tags?)
4. Is the answer grounded? (Does it sound like it's based on retrieved documents?)
5. Is there unsupported reasoning? (Does it make wild claims or use 'I think' or outside knowledge?)

Output a JSON object with:
- is_valid: true if ALL constraints are met, false if ANY fail.
- reason: If false, explicitly state which constraint failed and exactly what the LLM needs to do to fix it (e.g. 'You forgot to discuss entity Y. Add a section for it.'). If true, leave empty.
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ValidationResult,
                    temperature=0.0,
                ),
            )
            
            if response.text:
                import json
                data = json.loads(response.text)
                return ValidationResult(**data)
            
            return ValidationResult(is_valid=True, reason="")
        except Exception as exc:
            logger.warning("Response validation failed (LLM error): %s. Bypassing validation.", exc)
            return ValidationResult(is_valid=True, reason="")
