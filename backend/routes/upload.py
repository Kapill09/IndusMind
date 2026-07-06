from pathlib import Path
import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException, UploadFile

from backend.pipeline.ingestion_pipeline import (
    IngestionPipeline,
    IngestionPipelineError,
)
from backend.services.embedding_service import EmbeddingService
from backend.services.pdf_service import PDFService
from backend.services.vectordb_service import VectorDBService


# -----------------------------
# Router
# -----------------------------

router = APIRouter()
logger = logging.getLogger(__name__)

# Folder where uploaded PDFs are stored.
RAW_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

# Ensure the upload directory always exists.
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# Service Instances
# -----------------------------

# Create these only once.
pdf_service = PDFService()
embedding_service = EmbeddingService()
vectordb_service = VectorDBService()

# Pipeline orchestrates all services.
ingestion_pipeline = IngestionPipeline(
    pdf_service=pdf_service,
    embedding_service=embedding_service,
    vectordb_service=vectordb_service,
)


# -----------------------------
# Upload Endpoint
# -----------------------------

@router.post(
    "/upload",
    summary="Upload Industrial PDF",
    description="Upload manuals, SOPs, maintenance logs and automatically ingest them into the RAG knowledge base.",
)
async def upload_pdf(file: UploadFile):
    started_at = perf_counter()
    filename = file.filename or ""

    # Validate uploaded file.
    if (
        file.content_type != "application/pdf"
        and not filename.lower().endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed.",
        )

    # Safe filename prevents directory traversal.
    safe_filename = Path(filename).name
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename.")

    file_path = RAW_DATA_DIR / safe_filename

    file_size = 0
    logger.info("Upload started: filename=%s content_type=%s", safe_filename, file.content_type)

    # Save uploaded PDF.
    with file_path.open("wb") as saved_file:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            saved_file.write(chunk)

    # Automatically process the uploaded PDF.
    try:
        summary = ingestion_pipeline.ingest_document(file_path)

    except IngestionPipelineError as exc:
        logger.exception("PDF ingestion failed for %s", safe_filename)
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    total_time_ms = int((perf_counter() - started_at) * 1000)
    logger.info(
        "Upload completed: filename=%s size_bytes=%s chunks=%s total_latency_ms=%s",
        safe_filename,
        file_size,
        summary["chunks"],
        total_time_ms,
    )

    return {
        "success": True,
        "filename": safe_filename,
        "file_size": file_size,
        "ingestion": summary,
    }
