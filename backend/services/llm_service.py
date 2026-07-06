import logging
import os
from pathlib import Path
from time import perf_counter
from typing import Any

from dotenv import load_dotenv
from google import genai


GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
FALLBACK_ANSWER = "I couldn't find this information in the uploaded industrial documents."
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
        *,
        model: str = GEMINI_MODEL,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = model

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

    def generate_answer(self, question: str, retrieved_chunks: list[dict]) -> dict:
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
            return self._fallback_response()

        prompt = self._build_prompt(clean_question, clean_chunks)
        started_at = perf_counter()

        try:
            # The LLM receives only the question and retrieved context. Retrieval,
            # embeddings, ChromaDB, and PDF access remain outside this service.
            from google.genai import types

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=700,
                ),
            )
        except Exception as exc:
            raise LLMGenerationError("Gemini failed to generate an answer.") from exc

        answer = self._extract_text(response)
        if not answer:
            raise LLMGenerationError("Gemini returned an empty answer.")

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
    def _build_prompt(question: str, retrieved_chunks: list[dict]) -> str:
        """Build the grounded RAG prompt sent to Gemini."""

        context = "\n\n".join(
            LLMService._format_context_chunk(index, chunk)
            for index, chunk in enumerate(retrieved_chunks, start=1)
        )
        return f"""You are INDUS MIND, an AI assistant specialized in industrial maintenance, equipment manuals, SOPs, inspection reports, troubleshooting guides, and operational procedures.

Use only the provided context to answer the user's question.


SYSTEM INSTRUCTIONS

1. Answer ONLY using the provided context.
2. Never use outside knowledge.
3. Never invent or assume information.
4. If the answer cannot be found in the provided context, reply exactly:
   "{FALLBACK_ANSWER}"
5. Keep the answer concise: one short paragraph or up to five bullets.
6. Add citations after factual claims using this format: [source: <chunk_id>, page <page-or-range>].
7. Do not cite sources that are not present in the retrieved context.
8. If context is partial, state only what is supported and do not fill gaps.
9. If the retrieved context contains conflicting information, clearly state that the documents contain conflicting guidance instead of choosing one.

User Question:
{question}

Retrieved Context:
{context}

Answer:
"""

    @staticmethod
    def _format_context_chunk(index: int, chunk: dict) -> str:
        """Format one retrieved chunk with useful citation metadata."""

        page_start = chunk.get("page_start")
        page_end = chunk.get("page_end")
        page_label = LLMService._page_label(page_start, page_end)
        chunk_id = str(chunk.get("chunk_id", f"chunk_{index}"))
        text = str(chunk.get("text", "")).strip()

        return f"[Context Chunk {index} | chunk_id={chunk_id} | {page_label}]\n{text}"

    def _fallback_response(self) -> dict:
        """Return the standard grounded fallback without calling the model."""

        return {
            "answer": FALLBACK_ANSWER,
            "model": self.model,
            "context_chunks": 0,
            "sources": [],
            "success": True,
        }

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
