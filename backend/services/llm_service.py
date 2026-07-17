import logging
import os
import re
from pathlib import Path
from time import perf_counter
from typing import Any

from dotenv import load_dotenv
from google import genai
from backend.services.prompt_builder import PromptBuilder
from backend.config import GEMINI_API_KEY_ENV, FALLBACK_ANSWER


GEMINI_MODEL = "gemini-3.5-flash"
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(ENV_FILE)
logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Base exception for all LLM service errors."""


class LLMConfigurationError(LLMServiceError):
    """Raised when the LLM service is not configured correctly."""


class LLMValidationError(LLMServiceError):
    """Raised when answer generation input is invalid."""


class LLMGenerationError(LLMServiceError):
    """Raised when Gemini cannot generate an answer."""


class LLMService:
    """Generate grounded RAG answers from retrieved industrial document chunks.

    This service only converts a user question and already-retrieved context
    chunks into an answer using Gemini. It does not retrieve documents, generate
    embeddings, query ChromaDB, parse PDFs, or access the filesystem beyond
    loading configuration from the project environment file.

    Args:
        model: Gemini model name to use for answer generation.
        api_key: Optional Gemini API key. If omitted, GEMINI_API_KEY is read
            from the project .env file or process environment.
        client: Optional preconfigured Google GenAI client, useful for tests.

    Raises:
        LLMConfigurationError: If a Gemini API key is not available.
    """

    def __init__(
        self,
        model: str = GEMINI_MODEL,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.prompt_builder = PromptBuilder()

        # Load project-level environment variables without overriding values
        # already provided by the runtime environment.

        resolved_api_key = api_key or os.getenv(GEMINI_API_KEY_ENV)
        if client is None and not resolved_api_key:
            raise LLMConfigurationError(
                f"Missing Gemini API key. Set {GEMINI_API_KEY_ENV} in the .env file."
            )

        # Reuse one SDK client per service instance; request-specific data is
        # passed only when generate_answer is called.
        self.client = client or genai.Client(api_key=resolved_api_key)

    def generate_answer(
        self, 
        question: str, 
        retrieved_chunks: list[dict], 
        intent: str = "explanation", 
        output_format: str = "standard",
        correction_instruction: str | None = None
    ) -> dict:
        """Generate a concise grounded answer from retrieved chunks.

        Args:
            question: User question to answer.
            retrieved_chunks: Chunks returned by RetrievalService.

        Returns:
            Dictionary containing the answer, model name, context chunk count,
            and success status.

        Raises:
            LLMValidationError: If the question or retrieved chunks are invalid.
            LLMGenerationError: If Gemini fails to generate an answer.
        """

        clean_question = self._validate_question(question)
        clean_chunks = self._validate_chunks(retrieved_chunks)
        if not clean_chunks:
            logger.info("LLM generation skipped because no retrieved context was provided.")
            return self._fallback_response(clean_chunks)

        context_str = "\n\n".join(
            self._format_context_chunk(index, chunk)
            for index, chunk in enumerate(clean_chunks, start=1)
        )
        prompt = self.prompt_builder.build(
            clean_question, 
            context_str, 
            intent, 
            output_format,
            correction_instruction
        )
        started_at = perf_counter()

        import time
        from google.genai import types
        from google.genai.errors import APIError

        max_retries = 3
        backoff_seconds = 2

        for attempt in range(1, max_retries + 2):
            try:
                # The LLM receives only the question and retrieved context. Retrieval,
                # embeddings, ChromaDB, and PDF access remain outside this service.
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=1200,
                    ),
                )
                break
            except APIError as exc:
                if getattr(exc, "code", None) in (429, 503) and attempt <= max_retries:
                    logger.warning(
                        "Gemini API returned %s. Retry %s/%s in %ss...",
                        exc.code, attempt, max_retries, backoff_seconds
                    )
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2
                else:
                    logger.warning(
                        "Gemini generation failed, returning grounded fallback: %s",
                        exc,
                    )
                    return self._build_contextual_fallback(clean_question, clean_chunks)
            except Exception as exc:
                logger.warning(
                    "Gemini generation failed, returning grounded fallback: %s",
                    exc,
                )
                return self._build_contextual_fallback(clean_question, clean_chunks)

        answer = self._extract_text(response)
        if not answer:
            logger.warning("Gemini returned an empty answer; using contextual fallback.")
            return self._build_contextual_fallback(clean_question, clean_chunks)

        char_count = len(answer)
        word_count = len(answer.split())
        first_500 = answer[:500]
        last_500 = answer[-500:] if char_count > 500 else answer

        print("\n===== GEMINI RAW OUTPUT =====")
        print(f"Character Count: {char_count}")
        print(f"Word Count: {word_count}")
        print(f"First 500 chars:\n{first_500}")
        print(f"Last 500 chars:\n{last_500}")
        print("Contains Headings:")
        print(f"  Overview: {'Overview' in answer}")
        print(f"  Key Concepts: {'Key Concepts' in answer}")
        print(f"  Applications: {'Applications' in answer}")
        print(f"  Advantages: {'Advantages' in answer}")
        print(f"  Limitations: {'Limitations' in answer}")
        print(f"  Conclusion: {'Conclusion' in answer}")
        print("===== END GEMINI OUTPUT =====\n")

        logger.info(
            "LLM generation completed: model=%s context_chunks=%s latency_ms=%s",
            self.model,
            len(clean_chunks),
            int((perf_counter() - started_at) * 1000),
        )

        return {
            "answer": answer,
            "model": self.model,
            "context_chunks": len(clean_chunks),
            "sources": [
                {
                    "chunk_id": c.get("chunk_id"),
                    "page_start": c.get("page_start"),
                    "page_end": c.get("page_end"),
                }
                for c in clean_chunks
            ],
            "success": True,
        }

    @staticmethod
    def _validate_question(question: str) -> str:
        """Normalize and validate the user question."""

        if not isinstance(question, str):
            raise LLMValidationError("question must be a string.")

        clean_question = question.strip()
        if not clean_question:
            raise LLMValidationError("question cannot be empty.")

        return clean_question

    @staticmethod
    def _validate_chunks(retrieved_chunks: list[dict]) -> list[dict]:
        """Validate retrieved chunks before they are used as model context."""

        if not isinstance(retrieved_chunks, list):
            raise LLMValidationError("retrieved_chunks must be a list.")

        clean_chunks: list[dict] = []
        for index, chunk in enumerate(retrieved_chunks, start=1):
            if not isinstance(chunk, dict):
                raise LLMValidationError(f"retrieved_chunks item {index} must be a dictionary.")

            text = chunk.get("text")
            if not isinstance(text, str) or not text.strip():
                raise LLMValidationError(f"retrieved_chunks item {index} must contain text.")

            clean_chunks.append(chunk)

        return clean_chunks



    @staticmethod
    def _format_context_chunk(index: int, chunk: dict) -> str:
        """Format one retrieved chunk with useful citation metadata."""

        page_start = chunk.get("page_start")
        page_end = chunk.get("page_end")
        page_label = LLMService._page_label(page_start, page_end)
        chunk_id = str(chunk.get("chunk_id", f"chunk_{index}"))
        text = str(chunk.get("text", "")).strip()

        return f"[Context Chunk {index} | chunk_id={chunk_id} | {page_label}]\n{text}"

    def _fallback_response(self, retrieved_chunks: list[dict] | None = None) -> dict:
        """Return the standard grounded fallback without calling the model."""

        if retrieved_chunks:
            return self._build_contextual_fallback("", retrieved_chunks)

        return {
            "answer": FALLBACK_ANSWER,
            "model": self.model,
            "context_chunks": 0,
            "sources": [],
            "success": True,
        }

    def _build_contextual_fallback(self, question: str, retrieved_chunks: list[dict]) -> dict:
        """Build a concise grounded answer directly from retrieved chunks when the model is unavailable."""

        if not retrieved_chunks:
            return self._fallback_response([])

        ranked_chunks = sorted(
            retrieved_chunks,
            key=lambda chunk: self._chunk_relevance_score(question, chunk),
            reverse=True,
        )
        best_chunk = ranked_chunks[0]
        excerpt = self._make_excerpt(best_chunk)
        citation = self._citation_for_chunk(best_chunk)
        answer = f"Based on the retrieved document context, {excerpt}{citation}".strip()

        return {
            "answer": answer,
            "model": self.model,
            "context_chunks": len(retrieved_chunks),
            "sources": [
                {
                    "chunk_id": best_chunk.get("chunk_id"),
                    "page_start": best_chunk.get("page_start"),
                    "page_end": best_chunk.get("page_end"),
                }
                for best_chunk in ranked_chunks[:3]
            ],
            "success": True,
        }

    @staticmethod
    def _chunk_relevance_score(question: str, chunk: dict) -> float:
        """Estimate how relevant a chunk is to the question using simple token overlap."""

        if not question:
            return 1.0

        question_terms = set(re.findall(r"[a-z0-9]+", question.lower()))
        text_terms = set(re.findall(r"[a-z0-9]+", str(chunk.get("text", "")).lower()))
        if not question_terms:
            return 0.0
        return len(question_terms & text_terms)

    @staticmethod
    def _make_excerpt(chunk: dict) -> str:
        """Create a short, grounded excerpt from a chunk."""

        text = str(chunk.get("text", "")).strip()
        if not text:
            return "No supporting excerpt was available in the retrieved context."

        cleaned = re.sub(r"\s+", " ", text).strip()
        cleaned = cleaned[:480].rstrip()
        if len(cleaned) < len(text):
            cleaned = f"{cleaned}..."
        return cleaned

    @staticmethod
    def _citation_for_chunk(chunk: dict) -> str:
        """Append a compact citation for the selected chunk."""

        page_start = chunk.get("page_start")
        page_end = chunk.get("page_end")
        chunk_id = chunk.get("chunk_id")
        page_label = LLMService._page_label(page_start, page_end)
        if chunk_id:
            return f" [source: {chunk_id}, {page_label}]"
        return f" [{page_label}]"

    @staticmethod
    def _page_label(page_start: Any, page_end: Any) -> str:
        """Create a readable page label for prompt context."""

        if page_start is None and page_end is None:
            return "pages=unknown"
        if page_start == page_end or page_end is None:
            return f"page={page_start}"
        if page_start is None:
            return f"page={page_end}"

        return f"pages={page_start}-{page_end}"

    @staticmethod
    def _extract_text(response: Any) -> str:
        """Extract plain text from a Gemini SDK response."""

        text = getattr(response, "text", None)
        if isinstance(text, str):
            return text.strip()

        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            return output_text.strip()

        return ""
