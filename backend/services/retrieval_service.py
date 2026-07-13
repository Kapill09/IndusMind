import logging
import re
from collections import Counter
from typing import Any, Iterable, TypedDict

from backend.services.document_id_validation import sanitize_document_ids
from backend.services.embedding_service import EmbeddingService, EmbeddingServiceError
from backend.services.query_analyzer import QueryAnalyzer, StructuredQuery
from backend.services.vectordb_service import (
    VectorDBService,
    VectorDBServiceError,
    VectorSearchResult,
)


SEMANTIC_WEIGHT = 0.60
KEYWORD_WEIGHT = 0.25
STRUCTURED_WEIGHT = 0.15
NAVIGATION_SEMANTIC_WEIGHT = 0.35
NAVIGATION_KEYWORD_WEIGHT = 0.25
NAVIGATION_STRUCTURED_WEIGHT = 0.40
SEMANTIC_CANDIDATE_MULTIPLIER = 4
MAX_SEMANTIC_CANDIDATES = 50
MAX_KEYWORD_SCAN_CHUNKS = 5000
MAX_KEYWORD_CANDIDATES = 100
MAX_FILTER_CANDIDATES = 200
MIN_TEXT_FINGERPRINT_CHARS = 80

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
}

STRUCTURED_METADATA_FIELDS = {
    "problem_statement": "problem_statement_number",
    "section": "section_number",
    "chapter": "chapter_number",
    "figure": "figure_number",
    "table": "table_number",
}

logger = logging.getLogger(__name__)


class RetrievalResult(TypedDict):
    """One hybrid retrieval result returned to API callers."""

    chunk_id: str
    text: str
    page_start: int | None
    page_end: int | None
    metadata: dict[str, Any]
    distance: float | None
    score: float


class RetrievalResponse(TypedDict):
    """Structured response returned for a retrieval request."""

    question: str
    results: list[RetrievalResult]


class RetrievalServiceError(Exception):
    """Base exception for all retrieval service errors."""


class RetrievalValidationError(RetrievalServiceError):
    """Raised when the retrieval request is invalid."""


class RetrievalEmbeddingError(RetrievalServiceError):
    """Raised when the question embedding cannot be generated."""


class RetrievalSearchError(RetrievalServiceError):
    """Raised when hybrid retrieval cannot be completed."""


class RetrievalService:
    """Retrieve relevant INDUS MIND document chunks with hybrid ranking.

    The service combines structured query detection, metadata matching,
    keyword scoring, and semantic vector search. It keeps the public
    `retrieve(question, top_k)` contract unchanged and leaves embeddings,
    ChromaDB access, and answer generation in their existing services.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vectordb_service: VectorDBService,
        query_analyzer: QueryAnalyzer | None = None,
    ) -> None:
        self.embedding_service = embedding_service
        self.vectordb_service = vectordb_service
        self.query_analyzer = query_analyzer or QueryAnalyzer()

    def retrieve(
        self,
        question: str,
        top_k: int = 5,
        document_ids: list[str] | None = None,
    ) -> RetrievalResponse:
        """Retrieve the top K chunks using hybrid semantic and lexical ranking."""

        clean_question = self._validate_question(question)
        clean_top_k = self._validate_top_k(top_k)
        clean_document_ids = sanitize_document_ids(document_ids)
        semantic_limit = self._semantic_candidate_limit(clean_top_k)

        structured_query = self.query_analyzer.analyze(clean_question)
        if structured_query:
            logger.info(
                "Structured query detected: type=%s identifier=%s query=%r",
                structured_query.query_type,
                structured_query.identifier,
                structured_query.original_query,
            )

        try:
            where = None
            if clean_document_ids:
                # Chroma metadata filtering: match document_id in provided list
                where = {"document_id": {"$in": clean_document_ids}}
            all_chunks = self.vectordb_service.get_chunks(limit=MAX_KEYWORD_SCAN_CHUNKS, where=where)
        except VectorDBServiceError as exc:
            raise RetrievalSearchError("Failed to read chunks for hybrid retrieval.") from exc

        if structured_query:
            structured_candidates = self._structured_candidates(all_chunks, structured_query)
            if structured_candidates:
                logger.info(
                    "Structured retrieval returned %s candidates and is authoritative; skipping hybrid ranking.",
                    len(structured_candidates),
                )
                return {
                    "question": clean_question,
                    "results": self._format_structured_results(
                        structured_candidates,
                        structured_query,
                        clean_top_k,
                    ),
                }

        chunk_by_id = {chunk["chunk_id"]: chunk for chunk in all_chunks}
        structured_scores = self._metadata_scores(all_chunks, structured_query)
        keyword_scores = self._keyword_scores(clean_question, all_chunks, structured_query)
        keyword_scores = self._top_scores(keyword_scores, MAX_KEYWORD_CANDIDATES)

        logger.info("Keyword results: %s", self._score_log(keyword_scores))

        try:
            question_embedding = self.embedding_service.generate_embedding(clean_question)
        except EmbeddingServiceError as exc:
            raise RetrievalEmbeddingError("Failed to generate question embedding.") from exc

        semantic_results = self._semantic_results(
            question_embedding=question_embedding,
            top_k=semantic_limit,
            structured_scores=structured_scores,
            # pass document restriction through semantic search
            document_ids=clean_document_ids,
        )

        logger.info(
            "Semantic results: %s",
            [
                {
                    "chunk_id": result["chunk_id"],
                    "distance": result.get("distance"),
                }
                for result in semantic_results[:clean_top_k]
            ],
        )

        ranked_results = self._rank_results(
            semantic_results=semantic_results,
            chunk_by_id=chunk_by_id,
            keyword_scores=keyword_scores,
            structured_scores=structured_scores,
            structured_query=structured_query,
            top_k=clean_top_k,
        )

        logger.info(
            "Final ranked results: %s",
            [
                {
                    "chunk_id": result["chunk_id"],
                    "score": result["score"],
                    "page_start": result["page_start"],
                    "page_end": result["page_end"],
                }
                for result in ranked_results
            ],
        )

        # ── Scope validation logging ──────────────────────────────────
        returned_doc_ids = {
            str((r.get("metadata") or {}).get("document_id", ""))
            for r in ranked_results
        } - {""}

        scope_label = (
            f"Scoped to {clean_document_ids}"
            if clean_document_ids
            else "Entire Knowledge Base"
        )
        logger.info(
            "Retrieval scope audit: scope=%s applied_filter=%s returned_document_ids=%s",
            scope_label,
            where,
            sorted(returned_doc_ids),
        )

        if clean_document_ids:
            allowed = set(clean_document_ids)
            violations = returned_doc_ids - allowed
            if violations:
                logger.warning(
                    "SCOPE VIOLATION: retrieval returned chunks from documents "
                    "outside the requested scope. allowed=%s violations=%s",
                    sorted(allowed),
                    sorted(violations),
                )

        return {
            "question": clean_question,
            "results": ranked_results,
        }

    def _semantic_results(
        self,
        *,
        question_embedding: list[float],
        top_k: int,
        structured_scores: dict[str, float],
        document_ids: list[str] | None = None,
    ) -> list[VectorSearchResult]:
        """Run semantic search, narrowed by structured candidates when possible."""

        semantic_results: list[VectorSearchResult] = []
        structured_filter = self._chunk_id_filter(structured_scores)
        clean_document_ids = sanitize_document_ids(document_ids)

        if structured_filter:
            try:
                where_for_search = structured_filter
                if clean_document_ids:
                    where_for_search = {"$and": [structured_filter, {"document_id": {"$in": clean_document_ids}}]}
                semantic_results.extend(
                    self.vectordb_service.search(
                        query_embedding=question_embedding,
                        top_k=min(top_k, len(structured_scores)),
                        where=where_for_search,
                    )
                )
            except VectorDBServiceError:
                logger.warning("Filtered semantic search failed; falling back to global search.", exc_info=True)

        try:
            where_for_search = None
            if clean_document_ids:
                where_for_search = {"document_id": {"$in": clean_document_ids}}
            global_results = self.vectordb_service.search(
                query_embedding=question_embedding,
                top_k=top_k,
                where=where_for_search,
            )
        except VectorDBServiceError as exc:
            raise RetrievalSearchError("Failed to retrieve semantic candidates.") from exc

        semantic_results.extend(global_results)
        return self._dedupe_results(semantic_results)

    def _metadata_scores(
        self,
        chunks: list[VectorSearchResult],
        structured_query: StructuredQuery | None,
    ) -> dict[str, float]:
        """Score chunks that match structured query metadata or text."""

        if structured_query is None:
            return {}

        scores: dict[str, float] = {}
        for chunk in chunks:
            score = self._structured_score(chunk, structured_query)
            if score > 0:
                scores[chunk["chunk_id"]] = score

        logger.info("Structured metadata results: %s", self._score_log(scores))
        return scores

    def _structured_candidates(
        self,
        chunks: list[VectorSearchResult],
        structured_query: StructuredQuery,
    ) -> list[VectorSearchResult]:
        """Return chunks that match a structured query exactly or via structured phrase."""

        candidates: list[VectorSearchResult] = []
        for chunk in chunks:
            if self._is_structured_match(chunk, structured_query):
                candidates.append(chunk)

        if not candidates:
            return []

        return sorted(
            candidates,
            key=lambda chunk: self._structured_score(chunk, structured_query),
            reverse=True,
        )

    def _is_structured_match(
        self,
        chunk: VectorSearchResult,
        structured_query: StructuredQuery,
    ) -> bool:
        metadata = dict(chunk.get("metadata") or {})
        identifier = RetrievalService._normalize_identifier(structured_query.identifier)

        if structured_query.query_type == "page":
            page_number = RetrievalService._metadata_int(structured_query.identifier)
            page_start = RetrievalService._metadata_int(metadata.get("page_start"))
            page_end = RetrievalService._metadata_int(metadata.get("page_end")) or page_start
            return page_number is not None and page_start is not None and page_end is not None and page_start <= page_number <= page_end

        metadata_field = STRUCTURED_METADATA_FIELDS.get(structured_query.query_type)
        if metadata_field:
            metadata_identifier = RetrievalService._normalize_identifier(metadata.get(metadata_field))
            if metadata_identifier and metadata_identifier == identifier:
                return True

        searchable = RetrievalService._normalize_text(RetrievalService._searchable_text(chunk))
        phrase = RetrievalService._structured_phrase(structured_query)
        return bool(phrase and phrase in searchable)

    def _format_structured_results(
        self,
        results: list[VectorSearchResult],
        structured_query: StructuredQuery,
        top_k: int,
    ) -> list[RetrievalResult]:
        formatted: list[RetrievalResult] = []
        for chunk in results[:top_k]:
            score_components = {
                "semantic_score": 0.0,
                "keyword_score": 0.0,
                "structured_score": self._structured_score(chunk, structured_query),
            }
            formatted.append(
                self._format_result(
                    chunk,
                    combined_score=score_components["structured_score"],
                    score_components=score_components,
                )
            )
        return formatted

    def _keyword_scores(
        self,
        query: str,
        chunks: list[VectorSearchResult],
        structured_query: StructuredQuery | None,
    ) -> dict[str, float]:
        """Compute lightweight lexical scores over text, filename, and metadata."""

        query_terms = self._query_terms(query)
        if not query_terms:
            return {}

        query_phrase = self._normalize_text(query)
        structured_phrase = self._structured_phrase(structured_query)
        scores: dict[str, float] = {}

        for chunk in chunks:
            searchable_text = self._searchable_text(chunk)
            searchable_terms = set(self._tokenize(searchable_text))
            if not searchable_terms:
                continue

            matched_terms = sum(1 for term in query_terms if term in searchable_terms)
            term_score = matched_terms / len(query_terms)
            phrase_score = 0.0

            normalized_searchable = self._normalize_text(searchable_text)
            if query_phrase and query_phrase in normalized_searchable:
                phrase_score += 0.25
            if structured_phrase and structured_phrase in normalized_searchable:
                phrase_score += 0.35

            score = min(1.0, term_score + phrase_score)
            if score > 0:
                scores[chunk["chunk_id"]] = round(score, 4)

        return scores

    def _rank_results(
        self,
        *,
        semantic_results: list[VectorSearchResult],
        chunk_by_id: dict[str, VectorSearchResult],
        keyword_scores: dict[str, float],
        structured_scores: dict[str, float],
        structured_query: StructuredQuery | None,
        top_k: int,
    ) -> list[RetrievalResult]:
        """Fuse semantic, keyword, and structured scores into final ranking."""

        candidates: dict[str, VectorSearchResult] = {}
        semantic_distances: dict[str, float] = {}

        for result in semantic_results:
            chunk_id = result["chunk_id"]
            candidates[chunk_id] = result
            distance = result.get("distance")
            if distance is not None:
                semantic_distances[chunk_id] = min(
                    semantic_distances.get(chunk_id, float("inf")),
                    max(float(distance), 0.0),
                )

        for chunk_id in set(keyword_scores) | set(structured_scores):
            fallback_chunk = chunk_by_id.get(chunk_id)
            if fallback_chunk:
                candidates.setdefault(chunk_id, fallback_chunk)

        semantic_scores = self._normalize_distances(semantic_distances)
        keyword_scores = self._normalize_scores(keyword_scores)
        structured_scores = self._normalize_scores(structured_scores)
        weights = self._score_weights(structured_query)

        structured_match_ids = set()
        if structured_query and structured_scores:
            structured_match_ids = {
                chunk_id
                for chunk_id, score in structured_scores.items()
                if score >= 0.75
            }

        fused: list[tuple[float, VectorSearchResult, dict[str, float]]] = []
        for chunk_id, result in candidates.items():
            components = {
                "semantic_score": semantic_scores.get(chunk_id, 0.0),
                "keyword_score": keyword_scores.get(chunk_id, 0.0),
                "structured_score": structured_scores.get(chunk_id, 0.0),
            }
            combined_score = (
                weights["semantic"] * components["semantic_score"]
                + weights["keyword"] * components["keyword_score"]
                + weights["structured"] * components["structured_score"]
            )
            combined_score += self._exact_metadata_boost(result, structured_query)
            if structured_query and chunk_id in structured_match_ids:
                combined_score += 1.0 + (components["structured_score"] * 0.5)
            elif structured_query and structured_match_ids:
                combined_score -= 0.15
            fused.append((combined_score, result, components))

        fused.sort(key=lambda item: item[0], reverse=True)
        fused = self._dedupe_ranked_results(fused)
        
        # Enforce minimum relevance threshold to prevent context padding
        filtered_fused = [item for item in fused if item[0] >= 0.25]
        
        # If all chunks were below the threshold, return the best one so we have something
        if not filtered_fused and fused:
            filtered_fused = [fused[0]]
            
        return [
            self._format_result(result, combined_score=score, score_components=components)
            for score, result, components in filtered_fused[:top_k]
        ]

    @staticmethod
    def _validate_question(question: str) -> str:
        """Validate and normalize the user question."""

        if not isinstance(question, str):
            raise RetrievalValidationError("Question must be a string.")

        clean_question = question.strip()
        if not clean_question:
            raise RetrievalValidationError("Question cannot be empty.")

        return clean_question

    @staticmethod
    def _validate_top_k(top_k: int) -> int:
        """Validate requested number of retrieval results."""

        if not isinstance(top_k, int):
            raise RetrievalValidationError("top_k must be an integer.")
        if top_k <= 0:
            raise RetrievalValidationError("top_k must be greater than 0.")
        if top_k > 20:
            raise RetrievalValidationError("top_k cannot exceed 20.")

        return top_k

    @staticmethod
    def _format_result(
        result: VectorSearchResult,
        *,
        combined_score: float,
        score_components: dict[str, float],
    ) -> RetrievalResult:
        """Convert a ranked ChromaDB result into the public retrieval response."""

        metadata = dict(result.get("metadata") or {})
        metadata["retrieval_mode"] = "hybrid"
        metadata["semantic_score"] = round(score_components["semantic_score"], 4)
        metadata["keyword_score"] = round(score_components["keyword_score"], 4)
        metadata["structured_score"] = round(score_components["structured_score"], 4)
        metadata["combined_score"] = round(combined_score, 4)
        distance = result.get("distance")

        return {
            "chunk_id": result["chunk_id"],
            "text": result["text"],
            "page_start": RetrievalService._metadata_int(metadata.get("page_start")),
            "page_end": RetrievalService._metadata_int(metadata.get("page_end")),
            "metadata": metadata,
            "distance": float(distance) if distance is not None else None,
            "score": round(combined_score, 4),
        }

    @staticmethod
    def _structured_score(result: VectorSearchResult, structured_query: StructuredQuery) -> float:
        """Return a structured-navigation score for one chunk."""

        metadata = dict(result.get("metadata") or {})
        identifier = RetrievalService._normalize_identifier(structured_query.identifier)

        if structured_query.query_type == "page":
            page_number = RetrievalService._metadata_int(structured_query.identifier)
            page_start = RetrievalService._metadata_int(metadata.get("page_start"))
            page_end = RetrievalService._metadata_int(metadata.get("page_end")) or page_start
            if page_number is not None and page_start is not None and page_end is not None:
                if page_start <= page_number <= page_end:
                    return 1.0

        metadata_field = STRUCTURED_METADATA_FIELDS.get(structured_query.query_type)
        if metadata_field:
            metadata_identifier = RetrievalService._normalize_identifier(metadata.get(metadata_field))
            if metadata_identifier and metadata_identifier == identifier:
                return 1.0

        searchable = RetrievalService._normalize_text(RetrievalService._searchable_text(result))
        phrase = RetrievalService._structured_phrase(structured_query)
        if phrase and phrase in searchable:
            return 0.9
        if identifier and re.search(rf"\b{re.escape(identifier)}\b", searchable):
            type_token = structured_query.query_type.replace("_", " ")
            if type_token in searchable:
                return 0.75

        return 0.0

    @staticmethod
    def _normalize_distances(distances: dict[str, float]) -> dict[str, float]:
        """Convert absolute vector distances to similarity scores."""

        if not distances:
            return {}

        # Assuming cosine distance where max possible distance is 2.0.
        # similarity = 1.0 - (distance / 2.0)
        return {
            chunk_id: round(max(0.0, 1.0 - (distance / 2.0)), 4)
            for chunk_id, distance in distances.items()
        }

    @staticmethod
    def _normalize_scores(scores: dict[str, float]) -> dict[str, float]:
        """Normalize arbitrary positive component scores to a 0-1 range."""

        if not scores:
            return {}

        max_score = max(scores.values())
        if max_score <= 0:
            return {}

        return {
            chunk_id: round(max(min(score / max_score, 1.0), 0.0), 4)
            for chunk_id, score in scores.items()
        }

    @staticmethod
    def _score_weights(structured_query: StructuredQuery | None) -> dict[str, float]:
        """Use metadata more heavily when the user asks for document navigation."""

        if structured_query is None:
            return {
                "semantic": SEMANTIC_WEIGHT,
                "keyword": KEYWORD_WEIGHT,
                "structured": STRUCTURED_WEIGHT,
            }

        return {
            "semantic": NAVIGATION_SEMANTIC_WEIGHT,
            "keyword": NAVIGATION_KEYWORD_WEIGHT,
            "structured": NAVIGATION_STRUCTURED_WEIGHT,
        }

    @staticmethod
    def _exact_metadata_boost(
        result: VectorSearchResult,
        structured_query: StructuredQuery | None,
    ) -> float:
        """Small deterministic boost for exact metadata matches."""

        if structured_query is None:
            return 0.0

        metadata_field = STRUCTURED_METADATA_FIELDS.get(structured_query.query_type)
        if not metadata_field:
            return 0.0

        metadata = dict(result.get("metadata") or {})
        actual = RetrievalService._normalize_identifier(metadata.get(metadata_field))
        expected = RetrievalService._normalize_identifier(structured_query.identifier)
        return 0.05 if actual and actual == expected else 0.0

    @staticmethod
    def _metadata_int(value: Any) -> int | None:
        """Safely convert metadata values into integers."""

        if value is None or value == -1:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _semantic_candidate_limit(top_k: int) -> int:
        """Choose a broader semantic pool before final hybrid fusion."""

        return min(max(top_k * SEMANTIC_CANDIDATE_MULTIPLIER, top_k), MAX_SEMANTIC_CANDIDATES)

    @staticmethod
    def _chunk_id_filter(scores: dict[str, float]) -> dict[str, Any] | None:
        """Build a Chroma filter for structured candidate chunk IDs."""

        if not scores:
            return None

        chunk_ids = [
            chunk_id
            for chunk_id, _score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        ][:MAX_FILTER_CANDIDATES]
        if not chunk_ids:
            return None

        return {"chunk_id": {"$in": chunk_ids}}

    @staticmethod
    def _dedupe_results(results: Iterable[VectorSearchResult]) -> list[VectorSearchResult]:
        """Deduplicate Chroma records while preserving first occurrence order."""

        seen: set[str] = set()
        deduped: list[VectorSearchResult] = []
        for result in results:
            chunk_id = result["chunk_id"]
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            deduped.append(result)

        return deduped

    @staticmethod
    def _dedupe_ranked_results(
        ranked: list[tuple[float, VectorSearchResult, dict[str, float]]],
    ) -> list[tuple[float, VectorSearchResult, dict[str, float]]]:
        """Remove duplicate or near-duplicate chunks from final ranked results."""

        seen_ids: set[str] = set()
        seen_texts: set[str] = set()
        deduped: list[tuple[float, VectorSearchResult, dict[str, float]]] = []

        for score, result, components in ranked:
            chunk_id = result["chunk_id"]
            fingerprint = RetrievalService._text_fingerprint(result.get("text", ""))
            if chunk_id in seen_ids or (fingerprint and fingerprint in seen_texts):
                continue

            seen_ids.add(chunk_id)
            if fingerprint:
                seen_texts.add(fingerprint)
            deduped.append((score, result, components))

        return deduped

    @staticmethod
    def _text_fingerprint(text: str) -> str:
        """Create a compact text fingerprint for duplicate suppression."""

        normalized = RetrievalService._normalize_text(text)
        if len(normalized) < MIN_TEXT_FINGERPRINT_CHARS:
            return ""

        return normalized[:400]

    @staticmethod
    def _top_scores(scores: dict[str, float], limit: int) -> dict[str, float]:
        """Keep only the highest scoring lexical candidates."""

        return dict(sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit])

    @staticmethod
    def _score_log(scores: dict[str, float], limit: int = 10) -> list[dict[str, Any]]:
        """Return compact score data for retrieval logs."""

        return [
            {"chunk_id": chunk_id, "score": score}
            for chunk_id, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
        ]

    @staticmethod
    def _query_terms(query: str) -> list[str]:
        """Tokenize a query and remove low-value stopwords."""

        terms = [term for term in RetrievalService._tokenize(query) if term not in STOPWORDS]
        counts = Counter(terms)
        return list(counts)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Return lowercase alphanumeric tokens, preserving dotted numbers."""

        return re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower())

    @staticmethod
    def _searchable_text(result: VectorSearchResult) -> str:
        """Combine document text and metadata into one lexical search field."""

        metadata = dict(result.get("metadata") or {})
        metadata_values = " ".join(str(value) for value in metadata.values() if value is not None)
        return f"{result.get('text', '')} {metadata_values}"

    @staticmethod
    def _normalize_text(value: Any) -> str:
        """Normalize text for phrase matching."""

        return re.sub(r"\s+", " ", str(value).lower()).strip()

    @staticmethod
    def _normalize_identifier(value: Any) -> str:
        """Normalize structured identifiers such as 8, 2.1, or A3."""

        return str(value).strip().lower()

    @staticmethod
    def _structured_phrase(structured_query: StructuredQuery | None) -> str:
        """Build the canonical phrase for a structured query."""

        if structured_query is None:
            return ""

        return RetrievalService._normalize_text(
            f"{structured_query.query_type.replace('_', ' ')} {structured_query.identifier}"
        )
