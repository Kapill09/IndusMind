import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.services.document_service import (
    DocumentService,
    DocumentServiceError,
    DocumentServiceNotFoundError,
    DocumentServiceValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
document_service = DocumentService()


@router.get("", response_model=list[dict[str, Any]], status_code=status.HTTP_200_OK)
def list_documents() -> list[dict[str, Any]]:
    """Return a lightweight document inventory for the frontend."""

    try:
        return document_service.list_documents()
    except DocumentServiceError as exc:
        logger.exception("Failed to list documents")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/{document_id}", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def get_document(document_id: str) -> dict[str, Any]:
    """Return complete metadata for one indexed document."""

    try:
        return document_service.get_document(document_id)
    except DocumentServiceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DocumentServiceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentServiceError as exc:
        logger.exception("Failed to fetch document: %s", document_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str) -> None:
    """Delete all vectors associated with one document."""

    try:
        document_service.delete_document(document_id)
    except DocumentServiceValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DocumentServiceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentServiceError as exc:
        logger.exception("Failed to delete document: %s", document_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
