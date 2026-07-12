import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from backend.services.document_service import (
    DocumentService,
    DocumentServiceError,
    DocumentServiceNotFoundError,
    DocumentServiceValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])
api_documents_router = APIRouter(prefix="/api/documents", tags=["documents"])
document_service = DocumentService()
RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


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


@router.get("/preview", status_code=status.HTTP_200_OK)
def preview_document_pdf(document_id: str | None = None, filename: str | None = None) -> FileResponse:
    """Serve the raw PDF for a document so the frontend can preview it at the cited page."""

    resolved_document_id = (document_id or "").strip()
    if resolved_document_id:
        try:
            document = document_service.get_document(resolved_document_id)
        except (DocumentServiceValidationError, DocumentServiceNotFoundError) as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except DocumentServiceError as exc:
            logger.exception("Failed to resolve document for PDF preview: %s", resolved_document_id)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    else:
        document = None

    resolved_filename = (filename or (document or {}).get("filename") or "").strip()
    pdf_path = _resolve_pdf_path(resolved_filename, resolved_document_id)
    if not pdf_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF file was not found for this document.")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
    )


@api_documents_router.get("/{document_id}/pdf", status_code=status.HTTP_200_OK)
def stream_document_pdf(document_id: str) -> FileResponse:
    """Stream an uploaded PDF by document id for source inspection in the frontend."""

    try:
        document = document_service.get_document(document_id)
    except (DocumentServiceValidationError, DocumentServiceNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentServiceError as exc:
        logger.exception("Failed to resolve document for PDF streaming: %s", document_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    resolved_filename = str((document or {}).get("filename") or "").strip()
    pdf_path = _resolve_pdf_path(resolved_filename, document_id)
    if not pdf_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF file was not found for this document.")

    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=pdf_path.name,
    )


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


def _resolve_pdf_path(filename: str, document_id: str) -> Path:
    candidate_names = []
    if filename:
        candidate_names.append(Path(filename).name)
    if document_id:
        candidate_names.append(f"{document_id}.pdf")
        candidate_names.append(document_id)

    for candidate_name in candidate_names:
        if not candidate_name:
            continue
        candidate_path = (RAW_DATA_DIR / str(candidate_name)).resolve()
        if candidate_path.exists() and candidate_path.is_file() and str(candidate_path).startswith(str(RAW_DATA_DIR.resolve())):
            return candidate_path

    fallback_candidates = sorted(RAW_DATA_DIR.glob("*.pdf"))
    if fallback_candidates:
        return fallback_candidates[0]

    return RAW_DATA_DIR / f"{document_id}.pdf"
