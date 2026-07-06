import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StructuredQuery:
    """Structured navigation intent detected in a user query."""

    query_type: str
    identifier: str
    original_query: str


class QueryAnalyzer:
    """Detect document navigation patterns before semantic retrieval."""

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

    def analyze(self, query: str) -> StructuredQuery | None:
        """Return a structured query if the text contains a navigation pattern."""

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
