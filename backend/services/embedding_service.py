import os
from collections.abc import Sequence

from openai import APIConnectionError, APIStatusError, OpenAI, OpenAIError, RateLimitError
from openai import AuthenticationError as OpenAIAuthenticationError


EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"


class EmbeddingServiceError(Exception):
    """Base exception for all embedding service errors."""


class EmptyEmbeddingTextError(EmbeddingServiceError):
    """Raised when empty text is sent for embedding."""


class EmbeddingAuthenticationError(EmbeddingServiceError):
    """Raised when the OpenAI API key is missing or invalid."""


class EmbeddingRateLimitError(EmbeddingServiceError):
    """Raised when OpenAI rate limits the embedding request."""


class EmbeddingAPIError(EmbeddingServiceError):
    """Raised when OpenAI cannot generate embeddings for another API reason."""


class EmbeddingService:
    """Generate OpenAI embeddings for the INDUS MIND RAG pipeline.

    This service has one responsibility: convert validated text into embedding
    vectors. It intentionally does not store vectors, query ChromaDB, retrieve
    documents, or use LangChain.

    Args:
        api_key: Optional OpenAI API key. If omitted, the service reads
            OPENAI_API_KEY from the environment.
        model: OpenAI embedding model to use.
        client: Optional preconfigured OpenAI client, useful for tests.

    Raises:
        EmbeddingAuthenticationError: If no API key is available.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = EMBEDDING_MODEL,
        client: OpenAI | None = None,
    ) -> None:
        # Store the model name in one place so future upgrades are controlled.
        self.model = model

        # Read secrets from environment variables so keys are not hard-coded.
        resolved_api_key = api_key or os.getenv(OPENAI_API_KEY_ENV)
        if client is None and not resolved_api_key:
            raise EmbeddingAuthenticationError(
                f"Missing OpenAI API key. Set the {OPENAI_API_KEY_ENV} environment variable."
            )

        # Allow dependency injection in tests while using the official SDK in production.
        self.client = client or OpenAI(api_key=resolved_api_key)

    def generate_embedding(self, text: str) -> list[float]:
        """Generate one embedding vector for one text string.

        Args:
            text: Non-empty text to embed.

        Returns:
            The embedding vector exactly as returned by OpenAI.

        Raises:
            EmptyEmbeddingTextError: If the text is empty or only whitespace.
            EmbeddingAuthenticationError: If the API key is invalid.
            EmbeddingRateLimitError: If OpenAI rate limits the request.
            EmbeddingAPIError: If another OpenAI API failure occurs.
        """

        # Reuse batch generation so single and batch behavior stay consistent.
        return self.generate_embeddings([text])[0]

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple text strings.

        Args:
            texts: List of non-empty text strings to embed.

        Returns:
            Embedding vectors in the same order as the input texts, exactly as
            received from OpenAI.

        Raises:
            EmptyEmbeddingTextError: If the list is empty or contains empty text.
            EmbeddingAuthenticationError: If the API key is invalid.
            EmbeddingRateLimitError: If OpenAI rate limits the request.
            EmbeddingAPIError: If another OpenAI API failure occurs.
        """

        clean_texts = self._validate_texts(texts)

        try:
            # One API call for many chunks is faster and cheaper than calling per chunk.
            response = self.client.embeddings.create(
                model=self.model,
                input=clean_texts,
            )
        except OpenAIAuthenticationError as exc:
            raise EmbeddingAuthenticationError("OpenAI API key is invalid or unauthorized.") from exc
        except RateLimitError as exc:
            raise EmbeddingRateLimitError("OpenAI rate limit reached while generating embeddings.") from exc
        except (APIConnectionError, APIStatusError, OpenAIError) as exc:
            raise EmbeddingAPIError("OpenAI failed to generate embeddings.") from exc

        # Return only the raw embedding arrays; storage belongs to another service.
        return [item.embedding for item in response.data]

    @staticmethod
    def _validate_texts(texts: Sequence[str]) -> list[str]:
        """Validate embedding input before making a paid external API request."""

        if not texts:
            raise EmptyEmbeddingTextError("At least one text value is required for embedding.")

        clean_texts: list[str] = []
        for index, text in enumerate(texts, start=1):
            if not isinstance(text, str):
                raise EmptyEmbeddingTextError(f"Text item {index} must be a string.")

            # Strip whitespace because strings like "   " are empty for embedding.
            clean_text = text.strip()
            if not clean_text:
                raise EmptyEmbeddingTextError(f"Text item {index} is empty.")

            clean_texts.append(clean_text)

        return clean_texts
