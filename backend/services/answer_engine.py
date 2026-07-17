import logging
import re
from collections import Counter
from typing import Any, TypedDict

from backend.services.llm_service import LLMGenerationError, LLMService
from backend.services.retrieval_service import RetrievalResponse, RetrievalResult, RetrievalService

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 8
MAX_CONTEXT_TOKENS = 2200
MIN_CONFIDENCE_THRESHOLD = 45


class AnswerEngineResponse(TypedDict):
    """Structured response returned by the answer engine."""

    answer: str
    confidence: int
    citations: list[dict[str, Any]]
    context_used: list[dict[str, Any]]
    retrieval_summary: dict[str, Any]


class AnswerEngineError(Exception):
    """Base exception for all answer engine failures."""


class AnswerEngineValidationError(AnswerEngineError):
    """Raised when answer generation inputs are invalid."""


class AnswerEngineGenerationError(AnswerEngineError):
    """Raised when the answer engine cannot produce a grounded answer."""


class PromptBuilder:
    """Construct an enterprise-grade prompt for grounded answer generation."""

    def build_prompt(self, question: str, context_items: list[dict[str, Any]]) -> str:
        """Build a prompt that forces Gemini to answer strictly from supplied evidence."""

        if not question.strip():
            raise AnswerEngineValidationError("question cannot be empty.")
        if not context_items:
            raise AnswerEngineValidationError("context_items cannot be empty.")

        context_block = "\n\n".join(self._format_context_item(index, item) for index, item in enumerate(context_items, start=1))

        return f"""You are INDUS MIND, an enterprise industrial knowledge answer engine.

Your task is to answer the user's question using ONLY the supplied evidence.

Strict instructions:
1. Use only the provided context.
2. Never invent facts or infer unsupported details.
3. Always cite evidence with filename, page, chunk, and document id.
4. Never use external knowledge.
5. If the evidence is insufficient, respond exactly with: I couldn't find enough supporting evidence.
6. Keep the answer concise, factual, and grounded in the retrieved passages.
7. Prefer short paragraphs or bullet points.
8. If evidence conflicts, explicitly state that the supplied context conflicts.

User Question:
{question}

Supplied Context:
{context_block}

Answer:
"""

    @staticmethod
    def _format_context_item(index: int, item: dict[str, Any]) -> str:
        """Render a single context item in a citation-friendly format."""

        citation = item.get("citation", {})
        source = citation.get("filename", "unknown")
        page = citation.get("page")
        chunk = citation.get("chunk")
        document_id = citation.get("document")
        text = str(item.get("text", "")).strip()

        page_label = f", page {page}" if page is not None else ""
        chunk_label = f", chunk {chunk}" if chunk is not None else ""
        document_label = f", document {document_id}" if document_id else ""
        return f"[{index}] Source: {source}{page_label}{chunk_label}{document_label}\n{text}"


class AnswerEngine:
    """Orchestrate enterprise-grade answer generation from retrieval evidence.

    The answer engine consumes retrieval results from RetrievalService, removes
    duplicate context, ranks evidence by structured relevance, compresses the
    retained passages into a bounded token budget, merges adjacent chunks, and
    submits only the strongest evidence to Gemini with explicit citations.
    """

    def __init__(
        self,
        *,
        llm_service: LLMService | None = None,
        retrieval_service: RetrievalService | None = None,
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.retrieval_service = retrieval_service
        self.prompt_builder = PromptBuilder()

    def generate_answer(
        self,
        question: str,
        retrieval_response: RetrievalResponse | None = None,
        top_k: int = DEFAULT_TOP_K,
    ) -> AnswerEngineResponse:
        """Generate a grounded answer from existing retrieval output."""

        clean_question = self._validate_question(question)
        if retrieval_response is None:
            if self.retrieval_service is None:
                raise AnswerEngineValidationError(
                    "retrieval_response or retrieval_service must be provided."
                )
            try:
                retrieval_response = self.retrieval_service.retrieve(clean_question, top_k=top_k)
            except Exception as exc:
                raise AnswerEngineGenerationError("Failed to retrieve supporting evidence.") from exc

        results = list(retrieval_response.get("results", []) or [])
        if not results:
            return self._fallback_response(clean_question, retrieval_response)

        deduplicated = self._deduplicate_chunks(results)
        ranked = self._rank_chunks(deduplicated, clean_question)
        merged = self._merge_adjacent_chunks(ranked)
        context_items = self._compress_context(merged, clean_question)

        retrieval_summary = {
            "requested_top_k": top_k,
            "retrieved_chunks": len(results),
            "deduplicated_chunks": len(deduplicated),
            "ranked_chunks": len(ranked),
            "context_chunks": len(context_items),
            "documents": sorted({item["citation"]["document"] for item in context_items if item["citation"].get("document")}),
            "pages": sorted({item["citation"]["page"] for item in context_items if item["citation"].get("page") is not None}),
        }

        if not context_items:
            return self._fallback_response(clean_question, retrieval_response, retrieval_summary)

        confidence = self._calculate_confidence(context_items, retrieval_summary)

        prompt = self.prompt_builder.build_prompt(clean_question, context_items)
        try:
            answer_text = self._generate_with_gemini(prompt)
        except (LLMGenerationError, Exception) as exc:
            raise AnswerEngineGenerationError("Gemini failed to generate a grounded answer.") from exc

        if not answer_text or self._is_fallback_answer(answer_text):
            return self._fallback_response(clean_question, retrieval_response, retrieval_summary, confidence)

        citations = [item["citation"] for item in context_items]
        return {
            "answer": answer_text,
            "confidence": confidence,
            "citations": citations,
            "context_used": context_items,
            "retrieval_summary": retrieval_summary,
        }

    def _generate_with_gemini(self, prompt: str) -> str:
        """Generate a grounded answer using the configured LLM service client."""

        try:
            from google.genai import types

            response = self.llm_service.client.models.generate_content(
                model=self.llm_service.model,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=700),
            )
        except Exception as exc:
            raise LLMGenerationError("Gemini failed to generate an answer.") from exc

        if hasattr(response, "text") and isinstance(response.text, str) and response.text.strip():
            return response.text.strip()

        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            if parts:
                texts = []
                for part in parts:
                    text = getattr(part, "text", None)
                    if isinstance(text, str) and text.strip():
                        texts.append(text)
                if texts:
                    return "\n".join(texts).strip()

        return ""

    def _deduplicate_chunks(self, results: list[RetrievalResult]) -> list[dict[str, Any]]:
        """Remove repeated chunks while preserving the strongest version of each one."""

        seen: dict[tuple[str, str], dict[str, Any]] = {}
        for result in results:
            text = self._normalize_text(result.get("text", ""))
            chunk_id = str(result.get("chunk_id", "")).strip()
            metadata = result.get("metadata") or {}
            document_id = str(metadata.get("document_id", "")).strip()
            fingerprint = (document_id, text)
            if not text:
                continue
            existing = seen.get(fingerprint)
            if existing is None:
                seen[fingerprint] = {
                    "chunk_id": chunk_id,
                    "text": result.get("text", ""),
                    "score": float(result.get("score", 0.0) or 0.0),
                    "page_start": result.get("page_start"),
                    "page_end": result.get("page_end"),
                    "metadata": metadata,
                }
            else:
                existing["score"] = max(existing["score"], float(result.get("score", 0.0) or 0.0))
                if not existing.get("chunk_id") and chunk_id:
                    existing["chunk_id"] = chunk_id

        return list(seen.values())

    def _rank_chunks(self, chunks: list[dict[str, Any]], question: str) -> list[dict[str, Any]]:
        """Score each chunk using retrieval relevance and structured metadata cues."""

        query_terms = self._tokenize(question)
        ranked: list[dict[str, Any]] = []
        for chunk in chunks:
            metadata = chunk.get("metadata") or {}
            structured_score = self._structured_metadata_score(metadata)
            heading_score = self._heading_score(metadata)
            page_relevance_score = self._page_relevance_score(chunk, query_terms)
            semantic_score = self._normalize_score(chunk.get("score", 0.0))
            ranking_score = semantic_score + structured_score + heading_score + page_relevance_score
            ranked.append(
                {
                    **chunk,
                    "ranking_score": ranking_score,
                    "structured_score": structured_score,
                    "heading_score": heading_score,
                    "page_relevance_score": page_relevance_score,
                }
            )

        ranked.sort(
            key=lambda item: (
                -item["structured_score"],
                -item["heading_score"],
                -item["ranking_score"],
                item.get("page_start") if item.get("page_start") is not None else float("inf"),
            )
        )
        return ranked

    def _merge_adjacent_chunks(self, ranked_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Merge adjacent chunks from the same document and nearby pages."""

        if not ranked_chunks:
            return []

        merged: list[dict[str, Any]] = []
        current = dict(ranked_chunks[0])
        for chunk in ranked_chunks[1:]:
            if self._should_merge(current, chunk):
                current["text"] = self._merge_text(current.get("text", ""), chunk.get("text", ""))
                current["page_end"] = chunk.get("page_end") if chunk.get("page_end") is not None else current.get("page_end")
                current["ranking_score"] = max(current.get("ranking_score", 0.0), chunk.get("ranking_score", 0.0))
                current.setdefault("merged_chunks", []).append(chunk.get("chunk_id"))
            else:
                current.setdefault("merged_chunks", [current.get("chunk_id")])
                merged.append(current)
                current = dict(chunk)

        current.setdefault("merged_chunks", [current.get("chunk_id")])
        merged.append(current)
        return merged

    def _compress_context(self, chunks: list[dict[str, Any]], question: str) -> list[dict[str, Any]]:
        """Select the most relevant passages within the model token budget."""

        budget_tokens = MAX_CONTEXT_TOKENS
        context_items: list[dict[str, Any]] = []
        used_tokens = 0

        for chunk in chunks:
            compressed_text = self._compress_text(str(chunk.get("text", "")), question)
            estimated_tokens = self._estimate_token_count(compressed_text)
            if used_tokens + estimated_tokens > budget_tokens:
                remaining_budget = max(0, budget_tokens - used_tokens)
                if remaining_budget <= 0:
                    break
                compressed_text = self._truncate_text(compressed_text, remaining_budget)
                estimated_tokens = self._estimate_token_count(compressed_text)
                if not compressed_text:
                    continue

            citation = {
                "filename": self._resolve_filename(chunk),
                "page": chunk.get("page_start"),
                "chunk": chunk.get("chunk_id"),
                "document": self._resolve_document_id(chunk),
            }
            context_items.append(
                {
                    "text": compressed_text,
                    "citation": citation,
                    "score": chunk.get("ranking_score", 0.0),
                    "page_start": chunk.get("page_start"),
                    "page_end": chunk.get("page_end"),
                }
            )
            used_tokens += estimated_tokens
            if used_tokens >= budget_tokens:
                break

        return context_items

    def _compress_text(self, text: str, question: str) -> str:
        """Keep only the most relevant sentences or paragraphs from a chunk."""

        if not text.strip():
            return ""

        normalized_text = self._normalize_text(text)
        if self._estimate_token_count(normalized_text) <= 220:
            return normalized_text

        paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n", normalized_text) if segment.strip()]
        if not paragraphs:
            paragraphs = [normalized_text]

        query_terms = self._tokenize(question)
        scored: list[tuple[float, int, str]] = []
        for index, paragraph in enumerate(paragraphs):
            paragraph_score = 0.0
            for term in query_terms:
                if term.lower() in paragraph.lower():
                    paragraph_score += 1.0
            paragraph_score += min(1.0, len(paragraph.split()) / 60.0)
            scored.append((paragraph_score, index, paragraph))

        scored.sort(key=lambda item: (-item[0], item[1]))
        selected_paragraphs: list[str] = []
        for _, _, paragraph in scored:
            if self._estimate_token_count("\n\n".join(selected_paragraphs + [paragraph])) <= 220:
                selected_paragraphs.append(paragraph)
            else:
                break

        if not selected_paragraphs:
            return paragraphs[0][:800]
        return "\n\n".join(selected_paragraphs)

    def _calculate_confidence(self, context_items: list[dict[str, Any]], retrieval_summary: dict[str, Any]) -> int:
        """Calculate a 0-100 confidence score for the final answer."""

        if not context_items:
            return 0

        retrieval_component = self._normalize_score(sum(item.get("score", 0.0) for item in context_items) / len(context_items))
        document_counts = Counter(item["citation"].get("document") for item in context_items if item["citation"].get("document"))
        agreement_ratio = min(1.0, max(document_counts.values()) / max(1, len(context_items)))
        citation_consistency = min(1.0, (len(document_counts) / max(1, len(context_items))) + (agreement_ratio / 2.0))

        confidence_score = (0.45 * retrieval_component) + (0.25 * agreement_ratio) + (0.30 * citation_consistency)
        return int(round(min(100.0, max(0.0, confidence_score * 100))))

    def _fallback_response(
        self,
        question: str,
        retrieval_response: RetrievalResponse | None,
        retrieval_summary: dict[str, Any] | None = None,
        confidence: int | None = None,
    ) -> AnswerEngineResponse:
        """Return a safe fallback response when evidence is insufficient."""

        return {
            "answer": "I couldn't find enough supporting evidence.",
            "confidence": confidence if confidence is not None else 20,
            "citations": [],
            "context_used": [],
            "retrieval_summary": retrieval_summary or {
                "retrieved_chunks": len(retrieval_response.get("results", []) or []) if retrieval_response else 0,
                "context_chunks": 0,
            },
        }

    @staticmethod
    def _validate_question(question: str) -> str:
        """Normalize and validate the user question."""

        if not isinstance(question, str):
            raise AnswerEngineValidationError("question must be a string.")
        clean_question = question.strip()
        if not clean_question:
            raise AnswerEngineValidationError("question cannot be empty.")
        return clean_question

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize whitespace in chunk text before ranking or compression."""

        return re.sub(r"\s+", " ", str(text or "")).strip()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize a question into lowercase terms for relevance scoring."""

        return [token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if token]

    @staticmethod
    def _normalize_score(value: Any) -> float:
        """Normalize retrieval scores into a 0-1 range."""

        try:
            numeric_value = float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, numeric_value))

    @staticmethod
    def _structured_metadata_score(metadata: dict[str, Any]) -> float:
        """Reward chunks whose metadata contains structured identifiers."""

        structured_fields = (
            "problem_statement_number",
            "section_number",
            "chapter_number",
            "figure_number",
            "table_number",
        )
        score = 0.0
        for field in structured_fields:
            if metadata.get(field):
                score += 0.2
        if metadata.get("heading") or metadata.get("title"):
            score += 0.1
        return min(score, 1.0)

    @staticmethod
    def _heading_score(metadata: dict[str, Any]) -> float:
        """Reward chunks whose metadata contains clear heading information."""

        if metadata.get("heading") or metadata.get("title"):
            return 0.15
        return 0.0

    @staticmethod
    def _page_relevance_score(chunk: dict[str, Any], query_terms: list[str]) -> float:
        """Use page metadata as a mild relevance signal when available."""

        if not chunk.get("page_start") and not chunk.get("page_end"):
            return 0.0
        if not query_terms:
            return 0.05
        return 0.05

    @staticmethod
    def _should_merge(current: dict[str, Any], candidate: dict[str, Any]) -> bool:
        """Determine whether two chunks should be merged."""

        current_doc = str(current.get("metadata", {}).get("document_id", ""))
        candidate_doc = str(candidate.get("metadata", {}).get("document_id", ""))
        if current_doc != candidate_doc:
            return False

        current_start = current.get("page_start")
        candidate_start = candidate.get("page_start")
        current_end = current.get("page_end")
        candidate_end = candidate.get("page_end")

        if current_start is None or candidate_start is None or current_end is None:
            return False

        if candidate_start <= current_end + 1:
            return True
        if current_end is not None and candidate_end is not None and candidate_start <= current_end + 1:
            return True
        return False

    @staticmethod
    def _merge_text(first_text: str, second_text: str) -> str:
        """Combine two adjacent chunk texts with a separator."""

        segments = [segment.strip() for segment in [first_text, second_text] if segment and segment.strip()]
        if not segments:
            return ""
        return "\n\n".join(segments)

    @staticmethod
    def _estimate_token_count(text: str) -> int:
        """Estimate token count using a lightweight heuristic."""

        return max(1, len(text.split()))

    @staticmethod
    def _truncate_text(text: str, max_tokens: int) -> str:
        """Truncate text to a rough token budget."""

        words = text.split()
        if len(words) <= max_tokens:
            return text
        return " ".join(words[:max_tokens])

    @staticmethod
    def _resolve_filename(chunk: dict[str, Any]) -> str:
        """Resolve a display-friendly filename from chunk metadata."""

        metadata = chunk.get("metadata") or {}
        filename = metadata.get("filename")
        if isinstance(filename, str) and filename.strip():
            return filename.strip()
        return "unknown.pdf"

    @staticmethod
    def _resolve_document_id(chunk: dict[str, Any]) -> str:
        """Resolve the document id for a chunk."""

        metadata = chunk.get("metadata") or {}
        document_id = metadata.get("document_id")
        if isinstance(document_id, str) and document_id.strip():
            return document_id.strip()
        return "unknown"

    @staticmethod
    def _is_fallback_answer(answer: str) -> bool:
        """Detect if the LLM returned the fallback answer."""

        return "couldn't find enough supporting evidence" in answer.lower()
