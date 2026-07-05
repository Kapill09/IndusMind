from pathlib import Path
import logging

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

    # Validate uploaded file.
    if (
        file.content_type != "application/pdf"
        and not file.filename.lower().endswith(".pdf")
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed.",
        )

    # Safe filename prevents directory traversal.
    safe_filename = Path(file.filename).name

    print("=" * 60)
    print("UPLOAD ENDPOINT HIT")
    print(f"File: {safe_filename}")

    file_path = RAW_DATA_DIR / safe_filename

    file_size = 0

    # Save uploaded PDF.
    with file_path.open("wb") as saved_file:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            saved_file.write(chunk)

    # Automatically process the uploaded PDF.
    try:
        print("Starting ingestion pipeline...")
        summary = ingestion_pipeline.ingest_document(file_path)
        print("Pipeline completed successfully")
        print(summary)

    except IngestionPipelineError as exc:
        logger.exception("PDF ingestion failed for %s", safe_filename)
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return {
        "success": True,
        "filename": safe_filename,
        "file_size": file_size,
        "ingestion": summary,
    }
