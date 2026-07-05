import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.embedding_service import EmbeddingService
from backend.services.retrieval_service import (
    RetrievalEmbeddingError,
    RetrievalSearchError,
    RetrievalService,
    RetrievalValidationError,
)
from backend.services.vectordb_service import VectorDBService


# -----------------------------
# Router
# -----------------------------

router = APIRouter(
    prefix="/api",
    tags=["Question Answering"],
)   
logger = logging.getLogger(__name__)


# -----------------------------
# Request Models
# -----------------------------

class AskRequest(BaseModel):
    """Request body for semantic retrieval over the INDUS MIND knowledge base."""

    question: str = Field(
        ...,
        min_length=1,
        description="User question to retrieve relevant industrial knowledge chunks for.",
        examples=["How often should a centrifugal pump be lubricated?"],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of relevant chunks to return.",
        examples=[5],
    )


# -----------------------------
# Service Instances
# -----------------------------

# Create these once so the embedding model and ChromaDB collection are reused
# across requests instead of being reinitialized for every question.
embedding_service = EmbeddingService()
vectordb_service = VectorDBService()
retrieval_service = RetrievalService(
    embedding_service=embedding_service,
    vectordb_service=vectordb_service,
)


# -----------------------------
# Ask Endpoint
# -----------------------------

@router.post(
    "/ask",
    summary="Retrieve Relevant Industrial Knowledge",
    description=(
        "Accepts a user question, embeds it with the existing embedding service, "
        "searches the ChromaDB knowledge base, and returns the top matching chunks. "
        "This endpoint performs retrieval only and does not generate an LLM answer."
    ),
    responses={
        200: {
            "description": "Relevant chunks retrieved successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "question": "How often should a centrifugal pump be lubricated?",
                        "retrieval_time_ms": 23,
                        "results": [
                            {
                                "chunk_id": "pump_manual_12",
                                "text": "Lubricate pump bearings according to the maintenance schedule...",
                                "page_start": 2,
                                "page_end": 3,
                                "metadata": {
                                    "document_id": "pump_manual",
                                    "filename": "pump_manual.pdf",
                                    "chunk_index": 12,
                                },
                                "score": 0.91,
                            }
                        ],
                    }
                }
            },
        },
        400: {"description": "Invalid retrieval request."},
        500: {"description": "Embedding or vector search failed."},
    },
)
async def ask_question(request: AskRequest):
    """Retrieve the most relevant stored chunks for a user question."""

    start_time = perf_counter()

    try:
        retrieval = retrieval_service.retrieve(
            question=request.question,
            top_k=request.top_k,
        )
    except RetrievalValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RetrievalEmbeddingError as exc:
        logger.exception("Question embedding failed.")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate question embedding.",
        ) from exc
    except RetrievalSearchError as exc:
        logger.exception("Vector retrieval failed.")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve relevant chunks.",
        ) from exc

    retrieval_time_ms = int((perf_counter() - start_time) * 1000)

    return {
        "success": True,
        "question": retrieval["question"],
        "retrieval_time_ms": retrieval_time_ms,
        "results": retrieval["results"],
    }
