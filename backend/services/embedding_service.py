from collections.abc import Sequence
from typing import Any, ClassVar


EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class EmbeddingServiceError(Exception):
    """Base exception for all embedding service errors."""


class EmptyEmbeddingTextError(EmbeddingServiceError):
    """Raised when empty text is sent for embedding."""


class EmbeddingAuthenticationError(EmbeddingServiceError):
    """Reserved for authentication failures in embedding providers."""


class EmbeddingRateLimitError(EmbeddingServiceError):
    """Reserved for rate-limit failures in embedding providers."""


class EmbeddingAPIError(EmbeddingServiceError):
    """Raised when the embedding provider cannot generate embeddings."""


class EmbeddingService:
    """Generate local Sentence Transformer embeddings for the INDUS MIND RAG pipeline.

    This service has one responsibility: convert validated text into embedding
    vectors. It intentionally does not store vectors, query ChromaDB, retrieve
    documents, or use LangChain.

    Args:
        api_key: Accepted for backward compatibility. It is not used by the
            local Sentence Transformer implementation.
        model: Sentence Transformer model name to use.
        client: Optional preloaded Sentence Transformer model, useful for tests.
    """

    _model_cache: ClassVar[dict[str, Any]] = {}

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = EMBEDDING_MODEL,
        client: Any | None = None,
    ) -> None:
        # Keep the constructor compatible with the previous service so callers
        # do not need to change while the provider is swapped underneath.
        _ = api_key
        self.model = model
        self.client = client or self._get_model(model)

    def generate_embedding(self, text: str) -> list[float]:
        """Generate one embedding vector for one text string.

        Args:
            text: Non-empty text to embed.

        Returns:
            The embedding vector as a Python list of floats.

        Raises:
            EmptyEmbeddingTextError: If the text is empty or only whitespace.
            EmbeddingAPIError: If Sentence Transformers cannot generate an embedding.
        """

        # Reuse batch generation so single and batch behavior stay consistent.
        return self.generate_embeddings([text])[0]

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for multiple text strings.

        Args:
            texts: List of non-empty text strings to embed.

        Returns:
            Embedding vectors in the same order as the input texts as Python
            lists of floats.

        Raises:
            EmptyEmbeddingTextError: If the list is empty or contains empty text.
            EmbeddingAPIError: If Sentence Transformers cannot generate embeddings.
        """

        clean_texts = self._validate_texts(texts)

        try:
            embeddings = self.client.encode(
                clean_texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        except Exception as exc:
            raise EmbeddingAPIError("Sentence Transformers failed to generate embeddings.") from exc

        # Sentence Transformers returns a numpy array here; convert it before
        # leaving the service so downstream code receives plain Python lists.
        return self._to_python_embeddings(embeddings)

    @classmethod
    def _get_model(cls, model_name: str) -> Any:
        """Load and cache the Sentence Transformer model once per process."""

        if model_name not in cls._model_cache:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingAPIError(
                    "sentence-transformers is required for local embeddings."
                ) from exc

            try:
                cls._model_cache[model_name] = SentenceTransformer(model_name)
            except Exception as exc:
                raise EmbeddingAPIError(
                    f"Failed to load Sentence Transformer model '{model_name}'."
                ) from exc

        return cls._model_cache[model_name]

    @staticmethod
    def _validate_texts(texts: Sequence[str]) -> list[str]:
        """Validate embedding input before model inference."""

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

    @staticmethod
    def _to_python_embeddings(embeddings: Any) -> list[list[float]]:
        """Convert model output into plain Python lists of floats."""

        values = embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings
        return [[float(value) for value in vector] for vector in values]
