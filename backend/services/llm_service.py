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


<<<<<<< HEAD
GEMINI_MODEL = "gemini-2.0-flash"
=======
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
FALLBACK_ANSWER = "The retrieved documents do not contain sufficient information to answer this question."
>>>>>>> hackathon-final
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
        print("=" * 60)
        print("USING GEMINI MODEL:", self.model)
        print("=" * 60)
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

<<<<<<< HEAD
        parts = []

        parts = []

        for index, chunk in enumerate(clean_chunks, start=1):
            formatted = self._format_context_chunk(index, chunk)

            if formatted is None:
                print("BAD CHUNK:", chunk)
                continue

            parts.append(formatted)

        context_str = "\n\n".join(parts)
        prompt = self.prompt_builder.build(
            clean_question, 
            context_str, 
            intent, 
            output_format,
            correction_instruction
        )
=======
        # 1. Classify the question
        question_type = self._classify_question(clean_question)

        # 3. Score and sort chunks
        sorted_chunks = sorted(
        clean_chunks,
        key=lambda x: x.get("score", 0),
        reverse=True
        )

        # 4. Merge similar chunks
        merged_chunks = self._merge_similar_chunks(sorted_chunks)

        # 5. Limit context to the most relevant sections
        final_chunks = merged_chunks[:8]

        logger.info("=" * 80)
        logger.info("FINAL CHUNKS SENT TO GEMINI")

        for i, chunk in enumerate(final_chunks):
            logger.info(
                "[%d] %s | score=%.4f | %s",
                i + 1,
                chunk.get("metadata", {}).get("source", chunk.get("document_id")),
                chunk.get("score", 0),
                chunk.get("text", "")[:150].replace("\n", " ")
            )

        logger.info("=" * 80)

        prompt = self._build_prompt(clean_question, final_chunks)
        print("\n" + "=" * 120)
        print("🟢 QUESTION")
        print(clean_question)

        print("\n" + "=" * 120)
        print("🟢 QUESTION TYPE")
        print(question_type)

        print("\n" + "=" * 120)
        print(f"🟢 FINAL CHUNKS ({len(final_chunks)})")

        for i, chunk in enumerate(final_chunks, start=1):
            print(f"\n----- CHUNK {i} -----")
            print("Chunk ID :", chunk.get("chunk_id"))
            print("Document :", chunk.get("document_id"))
            print("Pages    :", chunk.get("page_start"), "-", chunk.get("page_end"))
            print("Score    :", chunk.get("score"))

            print("\nTEXT:\n")
            print(chunk.get("text"))

        print("\n" + "=" * 120)
        print("🟢 PROMPT SENT TO GEMINI")
        print(prompt)
        print("=" * 120 + "\n")
>>>>>>> hackathon-final
        started_at = perf_counter()

        import time
        from google.genai import types
        from google.genai.errors import APIError

<<<<<<< HEAD
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
                        temperature=0.2,
                        max_output_tokens=2500,
                        system_instruction=(
                            "You are an expert technical writer. You must answer the user's question "
                            "IN YOUR OWN WORDS. Synthesize the information. NEVER copy or reproduce "
                            "the retrieved text or OCR passages verbatim. NEVER echo metadata, chunk labels, "
                            "or passage numbers. Write a professional, standalone explanation."
                        )
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
                import traceback
                error_trace = traceback.format_exc()
                logger.warning(
                    "Gemini generation failed, returning grounded fallback:\n%s",
                    error_trace,
                )
                return self._build_contextual_fallback(clean_question, clean_chunks)

        answer = self._extract_text(response)
        if not answer.strip():
            logger.warning("Generated answer too short. Falling back.")
            return self._build_contextual_fallback(clean_question, clean_chunks)
        
        answer = answer.replace("Based on the retrieved document context,", "")
        answer = answer.replace("Based on the retrieved context,", "")
        answer = answer.replace("Document:", "")
        answer = answer.replace("Section:", "")
        answer = answer.replace("Chunk ID:", "")
=======
            logger.info("=" * 80)
            logger.info("PROMPT SENT TO GEMINI")
            logger.info(prompt)

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1200,
                ),
            )
        except Exception as exc:
            logger.warning(
                "Gemini generation failed, returning grounded fallback: %s",
                exc,
            )
            return self._build_contextual_fallback(clean_question, final_chunks)

        answer = self._extract_text(response)
        print("\n" + "=" * 120)
        print("🟢 GEMINI RESPONSE")
        print(answer)
        print("=" * 120 + "\n")

>>>>>>> hackathon-final
        if not answer:
            logger.warning("Gemini returned an empty answer; using contextual fallback.")
            return self._build_contextual_fallback(clean_question, final_chunks)

        char_count = len(answer)
        word_count = len(answer.split())
        first_500 = answer[:500]
        last_500 = answer[-500:] if char_count > 500 else answer



        logger.info(
            "LLM generation completed: model=%s context_chunks=%s latency_ms=%s",
            self.model,
            len(final_chunks),
            int((perf_counter() - started_at) * 1000),
        )

        return {
            "answer": answer,
            "model": self.model,
            "context_chunks": len(final_chunks),
            "sources": [
                {
                    "chunk_id": c.get("chunk_id"),
                    "page_start": c.get("page_start"),
                    "page_end": c.get("page_end"),
                }
                for c in final_chunks
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

<<<<<<< HEAD


    @staticmethod
    def _format_context_chunk(index: int, chunk: dict) -> str:
        text = str(chunk.get("text", "")).strip()
        
        clean_lines = []
        for line in text.split('\n'):
            lower_line = line.strip().lower()
            if lower_line.startswith((
                "source:", "page:", "document:", "chunk:", "chunk id:", 
                "filename:", "section:", "metadata:", "citation:"
            )):
                continue
            clean_lines.append(line)
            
        clean_text = "\n".join(clean_lines).strip()
        clean_text = re.sub(r'\[source:[^\]]+\]', '', clean_text, flags=re.IGNORECASE)
    
        return f"PASSAGE {index}\n\n{clean_text}"
=======
    @staticmethod
    def _classify_question(question: str) -> str:
        """Classify the user question into one of the supported types."""
        q_lower = question.lower()
        if any(term in q_lower for term in ["what is", "define", "definition", "meaning of"]):
            return "Definition"
        if any(term in q_lower for term in ["stand for", "full form", "acronym"]):
            return "Full Form"
        if any(term in q_lower for term in ["summarize", "summary"]):
            return "Summary"
        if any(term in q_lower for term in ["problem statement", "objective"]):
            return "Problem Statement"
        if any(term in q_lower for term in ["compare", "difference", "vs"]):
            return "Comparison"
        if any(term in q_lower for term in ["algorithm", "procedure", "how to", "implement"]):
            return "Implementation"
        if any(term in q_lower for term in ["security property"]):
            return "Security Property"
        if any(term in q_lower for term in ["protocol"]):
            return "Protocol"
        return "Explanation"

    @staticmethod
    def _merge_similar_chunks(chunks: list[dict]) -> list[dict]:
        """Merge multiple chunks defining the same concept to prevent redundancy."""
        merged_chunks = []
        seen_terms_sets = []

        for chunk in chunks:
            text = chunk.get("text", "")
            if not text:
                continue

            terms = set(re.findall(r"[a-z0-9]+", text.lower()))
            if not terms:
                continue

            is_duplicate = False
            for seen_terms in seen_terms_sets:
                overlap = len(terms & seen_terms)
                # Use a high threshold (90%) because stop words will artificially inflate overlap
                if overlap > 0.90 * len(terms) or overlap > 0.90 * len(seen_terms):
                    is_duplicate = True
                    break

            if not is_duplicate:
                merged_chunks.append(chunk)
                seen_terms_sets.append(terms)

        return merged_chunks

    @staticmethod
    def _build_prompt(question: str, retrieved_chunks: list[dict]) -> str:
        """Build the grounded RAG prompt sent to Gemini."""

        context = "\n\n".join(
            LLMService._format_context_chunk(index, chunk)
            for index, chunk in enumerate(retrieved_chunks, start=1)
        )
        return f"""You are an Industrial Knowledge Assistant.

You MUST answer ONLY using the retrieved context below.

Instructions:

- Carefully read ALL retrieved passages before answering.
- Choose the passage(s) that best answer the user's question.
- Combine information from multiple passages if necessary.
- Never assume information that is not present in the retrieved context.
- Never copy large paragraphs verbatim.
- Ignore document metadata such as:
  • Author names
  • Copyright notices
  • DOI numbers
  • Publication notes
  • References
  • Figure captions
unless the user explicitly asks for them.

Formatting Rules:

• Definition questions:
Start with a one-sentence definition followed by a short explanation.

• Explanation questions:
Use short paragraphs or bullet points.

• List questions:
Return a bullet list.

• Procedure questions:
Return numbered steps.

• Comparison questions:
Return a markdown table.

• Summary questions:
Return 4-8 concise bullet points.

If the answer is not present anywhere in the retrieved passages, reply ONLY with:

"{FALLBACK_ANSWER}"

----------------------------
USER QUESTION
----------------------------

{question}

----------------------------
RETRIEVED PASSAGES
----------------------------

{context}

----------------------------
FINAL ANSWER
----------------------------
"""

    @staticmethod
    def _format_context_chunk(index: int, chunk: dict) -> str:
        """Format one retrieved chunk."""

        text = str(chunk.get("text", "")).strip()
        page_start = chunk.get("page_start", "?")
        page_end = chunk.get("page_end", page_start)

        if page_start == page_end:
            page_info = f"Page {page_start}"
        else:
            page_info = f"Pages {page_start}-{page_end}"

        return f"""
        ==============================
        PASSAGE {index}
        Source: {chunk.get("document_id", "Unknown")}
        {page_info}
        ==============================

        {text}
        """
>>>>>>> hackathon-final

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
<<<<<<< HEAD
        citation = self._citation_for_chunk(best_chunk)
        answer = f"{excerpt}{citation}".strip()
=======
        answer = excerpt
>>>>>>> hackathon-final

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
