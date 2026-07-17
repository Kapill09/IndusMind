from pathlib import Path
import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException, UploadFile, BackgroundTasks

from backend.pipeline.ingestion_pipeline import (
    IngestionPipeline,
    IngestionPipelineError,
)
from backend.services.embedding_service import EmbeddingService
from backend.services.pdf_service import PDFService
from backend.services.vectordb_service import VectorDBService
from backend.services.task_state_service import TaskStateService


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

pdf_service = PDFService()
vectordb_service = VectorDBService()
task_state_service = TaskStateService()
ingestion_pipeline: IngestionPipeline | None = None


def get_ingestion_pipeline() -> IngestionPipeline:
    """Lazily initialize ingestion so app startup does not load embedding models."""

    global ingestion_pipeline
    if ingestion_pipeline is None:
        ingestion_pipeline = IngestionPipeline(
            pdf_service=pdf_service,
            embedding_service=EmbeddingService(),
            vectordb_service=vectordb_service,
        )

    return ingestion_pipeline

def run_ingestion_task(task_id: str, file_path: Path):
    try:
        task_state_service.update_task_status(task_id, "PROCESSING")
        summary = get_ingestion_pipeline().ingest_document(file_path)
        task_state_service.update_task_status(task_id, "COMPLETED", result=summary)
    except Exception as exc:
        logger.exception("PDF ingestion failed for task %s", task_id)
        task_state_service.update_task_status(task_id, "FAILED", error_message=str(exc))


# -----------------------------
# Upload Endpoint
# -----------------------------

@router.post(
    "/upload",
    summary="Upload Industrial PDF",
    description="Upload manuals, SOPs, maintenance logs and automatically ingest them into the RAG knowledge base in the background.",
)
async def upload_pdf(file: UploadFile, background_tasks: BackgroundTasks):
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

    # Automatically process the uploaded PDF in the background.
    task_id = task_state_service.create_task()
    background_tasks.add_task(run_ingestion_task, task_id, file_path)

    total_time_ms = int((perf_counter() - started_at) * 1000)
    logger.info(
        "Upload completed: filename=%s size_bytes=%s total_latency_ms=%s",
        safe_filename,
        file_size,
        total_time_ms,
    )

    return {
        "success": True,
        "task_id": task_id,
        "filename": safe_filename,
        "file_size": file_size,
        "message": "Document uploaded and ingestion started in the background.",
    }

@router.get(
    "/upload/status/{task_id}",
    summary="Check Ingestion Status",
    description="Check the status of an asynchronous background ingestion task.",
)
async def get_upload_status(task_id: str):
    task = task_state_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task
