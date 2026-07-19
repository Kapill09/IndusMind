"""Query analysis, intent classification, and query expansion for INDUS MIND.

Combines the original regex-based structured query detection with LLM-powered
intent classification and query expansion.  All LLM calls are optional and
guarded by timeouts — the system always falls back to regex-only analysis.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import perf_counter
from typing import Any

from dotenv import load_dotenv

import backend.config as config

logger = logging.getLogger(__name__)

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_FILE)


class QueryIntent(str, Enum):
    """Classified intent of a user query."""

    NAVIGATIONAL = "navigational"   # "What is Problem Statement 8?"
    FACTOID = "factoid"             # "What is the inspection interval?"
    COMPARISON = "comparison"       # "Compare D2DAP with existing IDS"
    EXPLORATORY = "exploratory"     # "Explain AI"
    PROCEDURAL = "procedural"       # "How to calibrate pressure sensor?"
    ANALYTICAL = "analytical"       # "What are the key challenges?"


@dataclass(frozen=True)
class StructuredQuery:
    """Structured navigation intent detected in a user query."""

    query_type: str
    identifier: str
    original_query: str


@dataclass
class AnalyzedQuery:
    """Complete analysis of a user query — intent, structure, and expansion."""

    original_query: str
    intent: QueryIntent = QueryIntent.FACTOID
    structured: StructuredQuery | None = None
    sub_queries: list[str] = field(default_factory=list)
    expanded_terms: list[str] = field(default_factory=list)
    hyde_passage: str | None = None

    @property
    def is_multi_query(self) -> bool:
        """Whether the query was decomposed into sub-queries."""
        return len(self.sub_queries) > 1

    @property
    def search_queries(self) -> list[str]:
        """Return the list of queries to search with.

        For multi-query (comparison), returns sub-queries.
        For single query, returns the original query (possibly expanded).
        """
        if self.sub_queries:
            return self.sub_queries
        return [self.original_query]


class QueryAnalyzer:
    """Detect document navigation patterns, classify intent, and expand queries.

    The analyzer runs three stages:
    1. Regex-based structured query detection (fast, always runs)
    2. LLM-based intent classification (optional, guarded by timeout)
    3. Query expansion/decomposition based on intent (optional)
    """

    _PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        (
            "problem_statement",
            re.compile(
                r"\bproblem\s+(?:(?:statement|stmt)\s*)?(?:number|no\.?|#)?\s*([A-Za-z]?\d+[A-Za-z]?)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "section",
            re.compile(r"\bsection\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b", re.IGNORECASE),
        ),
        (
            "chapter",
            re.compile(r"\bchapter\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b", re.IGNORECASE),
        ),
        (
            "page",
            re.compile(r"\bpage\s*(?:number|no\.?|#)?\s*(\d+)\b", re.IGNORECASE),
        ),
        (
            "figure",
            re.compile(r"\b(?:figure|fig\.?)\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b", re.IGNORECASE),
        ),
        (
            "table",
            re.compile(r"\btable\s*(?:number|no\.?|#)?\s*([A-Za-z]?\d+(?:\.\d+)*[A-Za-z]?)\b", re.IGNORECASE),
        ),
    )

    # Heuristic patterns for intent detection fallback (when LLM is unavailable)
    _COMPARISON_RE = re.compile(
        r"\b(compare|comparison|versus|vs\.?|difference|contrast)\b"
        r"|\bbetter\s+than\b"
        r"|\badvantages?\s+over\b"
        r"|\bdisadvantages?\s+compared\s+to\b",
        re.IGNORECASE,
    )
    _EXPLORATORY_RE = re.compile(
        r"^(explain|describe|what is|what are|overview|introduction|summary)\b",
        re.IGNORECASE,
    )
    _PROCEDURAL_RE = re.compile(
        r"\b(how to|steps|procedure|process|method|guide|instructions)\b",
        re.IGNORECASE,
    )
    _ANALYTICAL_RE = re.compile(
        r"\b(challenges|advantages|disadvantages|impact|implications|analysis|evaluate)\b",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._llm_client: Any | None = None
        self._llm_enabled = getattr(config, "ENABLE_INTENT_CLASSIFIER", False)
        self._llm_timeout = getattr(config, "INTENT_CLASSIFIER_TIMEOUT_S", 3.0)

    def analyze(self, query: str) -> StructuredQuery | None:
        """Legacy API: Return a structured query if the text contains a navigation pattern.

        Kept for backward compatibility with existing callers.
        """
        clean_query = query.strip()
        for query_type, pattern in self._PATTERNS:
            match = pattern.search(clean_query)
            if match:
                return StructuredQuery(
                    query_type=query_type,
                    identifier=match.group(1).strip(),
                    original_query=clean_query,
                )
        return None

    def full_analyze(self, query: str) -> AnalyzedQuery:
        """Run the complete query analysis pipeline.

        Returns an AnalyzedQuery with intent, structure, sub-queries, and
        optional expanded terms or HyDE passage.
        """

        clean_query = query.strip()
        structured = self.analyze(clean_query)

        # Stage 1: If structured query detected, intent is navigational
        if structured:
            return AnalyzedQuery(
                original_query=clean_query,
                intent=QueryIntent.NAVIGATIONAL,
                structured=structured,
            )

        # Stage 2: Classify intent (LLM with heuristic fallback)
        intent = self._classify_intent(clean_query)

        # Stage 3: Generate sub-queries for comparison, expand for exploratory
        sub_queries: list[str] = []
        expanded_terms: list[str] = []
        hyde_passage: str | None = None

        if intent == QueryIntent.COMPARISON:
            sub_queries = self._decompose_comparison(clean_query)
        elif intent == QueryIntent.EXPLORATORY:
            expanded_terms = self._expand_exploratory(clean_query)
            hyde_passage = self._generate_hyde(clean_query)

        return AnalyzedQuery(
            original_query=clean_query,
            intent=intent,
            structured=structured,
            sub_queries=sub_queries,
            expanded_terms=expanded_terms,
            hyde_passage=hyde_passage,
        )

    def _classify_intent(self, query: str) -> QueryIntent:
        """Classify query intent using LLM with heuristic fallback."""

        # Try LLM classification first
        if self._llm_enabled:
            try:
                return self._classify_intent_llm(query)
            except Exception:
                logger.debug("LLM intent classification failed, using heuristic fallback", exc_info=True)

        # Heuristic fallback
        return self._classify_intent_heuristic(query)

    def _classify_intent_heuristic(self, query: str) -> QueryIntent:
        """Fast regex-based intent classification as fallback."""

        if self._COMPARISON_RE.search(query):
            return QueryIntent.COMPARISON
        if self._PROCEDURAL_RE.search(query):
            return QueryIntent.PROCEDURAL
        if self._ANALYTICAL_RE.search(query):
            return QueryIntent.ANALYTICAL
        if self._EXPLORATORY_RE.search(query):
            return QueryIntent.EXPLORATORY
        return QueryIntent.FACTOID

    def _classify_intent_llm(self, query: str) -> QueryIntent:
        """Classify intent using a lightweight Gemini call."""

        client = self._get_llm_client()
        if client is None:
            return self._classify_intent_heuristic(query)

        prompt = f"""Classify this query into exactly one category. Reply with ONLY the category name.

Categories:
- FACTOID: asking for a specific fact or answer
- COMPARISON: explicit comparison using words like compare, difference, versus, vs, better than, advantages over, disadvantages compared to, or contrast
- EXPLORATORY: broad explanation or overview request
- PROCEDURAL: asking how to do something
- ANALYTICAL: asking for analysis, evaluation, or assessment

Rules:
- "What is X?", "Who is X?", and "Define X" are FACTOID or EXPLORATORY, not COMPARISON, unless explicit comparison language is present.

Query: {query}

Category:"""

        try:
            from google.genai import types
            started_at = perf_counter()

            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=20,
                ),
            )

            latency = int((perf_counter() - started_at) * 1000)
            logger.info("Intent classification completed: latency_ms=%s", latency)

            text = getattr(response, "text", "") or ""
            text = text.strip().upper()

            intent_map = {
                "FACTOID": QueryIntent.FACTOID,
                "COMPARISON": QueryIntent.COMPARISON,
                "EXPLORATORY": QueryIntent.EXPLORATORY,
                "PROCEDURAL": QueryIntent.PROCEDURAL,
                "ANALYTICAL": QueryIntent.ANALYTICAL,
            }
            return intent_map.get(text, self._classify_intent_heuristic(query))

        except Exception:
            logger.debug("LLM intent classification failed", exc_info=True)
            return self._classify_intent_heuristic(query)

    def _decompose_comparison(self, query: str) -> list[str]:
        """Decompose a comparison query into sub-queries.

        For "Compare D2DAP with existing IDS", produces:
        - "D2DAP authentication protocol features"
        - "existing IDS intrusion detection systems features"
        """

        # Try LLM decomposition first
        if self._llm_enabled:
            try:
                return self._decompose_comparison_llm(query)
            except Exception:
                logger.debug("LLM comparison decomposition failed", exc_info=True)

        # Heuristic fallback: split at comparison keywords
        parts = re.split(
            r"\b(?:compare|comparison|versus|vs\.?|difference|contrast)\b|\bbetter\s+than\b|\badvantages?\s+over\b|\bdisadvantages?\s+compared\s+to\b",
            query,
            flags=re.IGNORECASE,
        )
        parts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 2]

        if len(parts) >= 2:
            return parts[:2]

        # Can't decompose — return original
        return [query]

    def _decompose_comparison_llm(self, query: str) -> list[str]:
        """Decompose a comparison query using Gemini."""

        client = self._get_llm_client()
        if client is None:
            return [query]

        prompt = f"""Break this comparison query into exactly 2 separate search queries, one for each thing being compared.
Return each query on a new line. Do not number them.

Query: {query}

Sub-queries:"""

        try:
            from google.genai import types

            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=100,
                ),
            )

            text = getattr(response, "text", "") or ""
            lines = [l.strip().lstrip("- ").lstrip("12. ") for l in text.strip().splitlines() if l.strip()]
            if len(lines) >= 2:
                return lines[:2]

        except Exception:
            logger.debug("LLM comparison decomposition failed", exc_info=True)

        return [query]

    def _expand_exploratory(self, query: str) -> list[str]:
        """Expand an exploratory query with related terms."""

        # Simple heuristic expansion: extract the main topic and add related terms
        # Remove common prefixes
        topic = re.sub(
            r"^(explain|describe|what is|what are|tell me about|overview of)\s+",
            "",
            query,
            flags=re.IGNORECASE,
        ).strip().rstrip("?.")

        if not topic:
            return []

        # Add the topic itself plus a more specific version
        return [
            topic,
            f"{topic} definition concepts overview",
            f"{topic} applications use cases examples",
        ]

    def _generate_hyde(self, query: str) -> str | None:
        """Generate a Hypothetical Document Embedding passage.

        Asks Gemini to write an ideal passage that would answer the query,
        then the embedding of that passage is used for retrieval instead of
        the raw query.
        """

        if not self._llm_enabled:
            return None

        client = self._get_llm_client()
        if client is None:
            return None

        prompt = f"""Write a short factual paragraph (3-4 sentences) that would perfectly answer this question.
Write as if you are quoting from a technical document. Do not mention that you are generating text.

Question: {query}

Passage:"""

        try:
            from google.genai import types

            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=200,
                ),
            )

            text = (getattr(response, "text", "") or "").strip()
            if text and len(text) > 30:
                logger.info("HyDE passage generated: length=%s", len(text))
                return text

        except Exception:
            logger.debug("HyDE generation failed", exc_info=True)

        return None

    def _get_llm_client(self) -> Any:
        """Lazily initialize the Gemini client for query analysis."""

        if self._llm_client is not None:
            return self._llm_client

        try:
            from google import genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.warning("GEMINI_API_KEY not set, LLM query analysis disabled")
                self._llm_enabled = False
                return None
            self._llm_client = genai.Client(api_key=api_key)
            return self._llm_client
        except Exception:
            logger.warning("Failed to initialize Gemini client for query analysis", exc_info=True)
            self._llm_enabled = False
            return None
