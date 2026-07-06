import logging
from collections import defaultdict
from typing import Any

from backend.services.vectordb_service import VectorDBService, VectorDBServiceError

logger = logging.getLogger(__name__)


class DocumentServiceError(Exception):
    """Base exception for document service failures."""


class DocumentServiceValidationError(DocumentServiceError):
    """Raised when a document identifier is invalid."""


class DocumentServiceNotFoundError(DocumentServiceError):
    """Raised when a requested document does not exist."""


class DocumentService:
    """Aggregate vector-store chunks into document-level metadata.

    This service is responsible for reading chunk records from VectorDBService,
    grouping them by document_id, and producing stable document summaries for
    the API layer. It does not directly manipulate ChromaDB beyond delegating
    to VectorDBService for document deletion.
    """

    def __init__(self, vectordb_service: VectorDBService | None = None) -> None:
        self.vectordb_service = vectordb_service or VectorDBService()

    def list_documents(self) -> list[dict[str, Any]]:
        """Return a document-level overview for every indexed document."""

        try:
            chunks = self.vectordb_service.get_chunks()
        except VectorDBServiceError as exc:
            logger.exception("Failed to read vector chunks for document listing")
            raise DocumentServiceError("Unable to read indexed documents from the vector store.") from exc

        documents = self._group_chunks(chunks)
        logger.info("Listed %s document(s) from vector store", len(documents))
        return documents

    def get_document(self, document_id: str) -> dict[str, Any]:
        """Return the aggregated metadata for one document."""

        clean_document_id = self._validate_document_id(document_id)
        documents = self.list_documents()

        for document in documents:
            if document["document_id"] == clean_document_id:
                return document

        raise DocumentServiceNotFoundError(f"Document '{clean_document_id}' was not found.")

    def delete_document(self, document_id: str) -> None:
        """Delete all chunks that belong to a single document."""

        clean_document_id = self._validate_document_id(document_id)

        try:
            self.vectordb_service.delete_document(clean_document_id)
        except VectorDBServiceError as exc:
            logger.exception("Failed to delete document from vector store: %s", clean_document_id)
            raise DocumentServiceError(
                f"Unable to delete document '{clean_document_id}' from the vector store."
            ) from exc

        logger.info("Deleted document from vector store: %s", clean_document_id)

    def _group_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Group chunk results by document_id and aggregate document metadata."""

        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for chunk in chunks:
            metadata = chunk.get("metadata") or {}
            document_id = str(metadata.get("document_id", "")).strip()
            if not document_id:
                continue

            groups[document_id].append(chunk)

        documents: list[dict[str, Any]] = []
        for document_id, document_chunks in sorted(groups.items()):
            metadata = document_chunks[0].get("metadata") or {}
            documents.append(
                {
                    "document_id": document_id,
                    "filename": self._resolve_filename(metadata, document_chunks),
                    "pages": self._infer_total_pages(document_chunks),
                    "chunks": len(document_chunks),
                    "status": "indexed",
                    "uploaded_at": self._resolve_uploaded_at(metadata),
                    "collection": self.vectordb_service.collection_name,
                }
            )

        return documents

    @staticmethod
    def _resolve_filename(metadata: dict[str, Any], document_chunks: list[dict[str, Any]]) -> str:
        """Resolve the most useful filename for a document from metadata."""

        filename = metadata.get("filename")
        if isinstance(filename, str) and filename.strip():
            return filename.strip()

        for chunk in document_chunks:
            candidate = (chunk.get("metadata") or {}).get("filename")
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

        return "unknown.pdf"

    @staticmethod
    def _resolve_uploaded_at(metadata: dict[str, Any]) -> str | None:
        """Return a known upload timestamp if one exists in metadata."""

        for key in ("uploaded_at", "created_at", "ingested_at", "timestamp"):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    @staticmethod
    def _infer_total_pages(document_chunks: list[dict[str, Any]]) -> int:
        """Infer the document page count from chunk metadata when possible."""

        max_page = 0
        for chunk in document_chunks:
            metadata = chunk.get("metadata") or {}
            page_start = metadata.get("page_start")
            page_end = metadata.get("page_end")

            if isinstance(page_start, int | float) and not isinstance(page_start, bool):
                max_page = max(max_page, int(page_start))
            if isinstance(page_end, int | float) and not isinstance(page_end, bool):
                max_page = max(max_page, int(page_end))

        return max_page

    @staticmethod
    def _validate_document_id(document_id: str) -> str:
        """Normalize and validate a document identifier."""

        if not isinstance(document_id, str):
            raise DocumentServiceValidationError("document_id must be a string.")

        clean_document_id = document_id.strip()
        if not clean_document_id:
            raise DocumentServiceValidationError("document_id is required.")

        return clean_document_id
