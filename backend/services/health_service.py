import logging
from typing import Any

from backend.services.embedding_service import EmbeddingService, EmbeddingServiceError
from backend.services.vectordb_service import VectorDBService, VectorDBServiceError
from backend.services.llm_service import LLMService, LLMConfigurationError

logger = logging.getLogger(__name__)


class HealthServiceError(Exception):
    """Base exception for health checks."""


class HealthService:
    """Evaluate API health for the core knowledge pipeline components."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vectordb_service: VectorDBService | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self.embedding_service = embedding_service
        self.vectordb_service = vectordb_service
        self.llm_service = llm_service

    def get_health(self) -> dict[str, Any]:
        """Return the current health status of the core backend services."""

        gemini_status = self._check_gemini()
        embedding_status = self._check_embeddings()
        chroma_status = self._check_chroma()
        vectors = self._count_vectors()

        return {
            "gemini": gemini_status,
            "embeddings": embedding_status,
            "chroma": chroma_status,
            "vectors": vectors,
        }

    def _check_gemini(self) -> str:
        """Check whether Gemini can be initialized with the configured credentials."""

        try:
            if self.llm_service is None:
                self.llm_service = LLMService()
            return "healthy"
        except LLMConfigurationError:
            return "degraded"
        except Exception:
            logger.exception("Unexpected Gemini health check failure")
            return "degraded"

    def _check_embeddings(self) -> str:
        """Check whether the embedding service is available."""

        try:
            if self.embedding_service is None:
                self.embedding_service = EmbeddingService()
            return "healthy"
        except EmbeddingServiceError:
            return "degraded"
        except Exception:
            logger.exception("Unexpected embedding health check failure")
            return "degraded"

    def _check_chroma(self) -> str:
        """Check whether ChromaDB is reachable."""

        try:
            if self.vectordb_service is None:
                self.vectordb_service = VectorDBService()
            self.vectordb_service.count_documents()
            return "healthy"
        except VectorDBServiceError:
            return "degraded"
        except Exception:
            logger.exception("Unexpected ChromaDB health check failure")
            return "degraded"

    def _count_vectors(self) -> int:
        """Return the current number of stored vectors."""

        try:
            if self.vectordb_service is None:
                self.vectordb_service = VectorDBService()
            return self.vectordb_service.count_documents()
        except VectorDBServiceError:
            return 0
        except Exception:
            logger.exception("Unexpected vector count failure")
            return 0
