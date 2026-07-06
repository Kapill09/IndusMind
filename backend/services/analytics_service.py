import logging
from typing import Any

from backend.services.document_service import DocumentService, DocumentServiceError

logger = logging.getLogger(__name__)


class AnalyticsServiceError(Exception):
    """Base exception for analytics service failures."""


class AnalyticsService:
    """Compute document-level analytics from the vector-backed document index."""

    def __init__(self, document_service: DocumentService | None = None) -> None:
        self.document_service = document_service or DocumentService()

    def get_analytics(self) -> dict[str, Any]:
        """Return aggregate analytics for the indexed knowledge base."""

        try:
            documents = self.document_service.list_documents()
        except DocumentServiceError as exc:
            logger.exception("Failed to load documents for analytics")
            raise AnalyticsServiceError("Unable to compute analytics from the vector store.") from exc

        total_documents = len(documents)
        total_pages = sum(int(document.get("pages") or 0) for document in documents)
        total_chunks = sum(int(document.get("chunks") or 0) for document in documents)
        total_vectors = total_chunks

        avg_chunks = round(total_chunks / total_documents, 2) if total_documents else 0.0
        avg_pages = round(total_pages / total_documents, 2) if total_documents else 0.0

        return {
            "documents": total_documents,
            "pages": total_pages,
            "chunks": total_chunks,
            "vectors": total_vectors,
            "avg_chunks": avg_chunks,
            "avg_pages": avg_pages,
        }
