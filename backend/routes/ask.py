import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.pipeline.rag_pipeline import (
    RAGPipeline,
    RAGPipelineGenerationError,
    RAGPipelineRetrievalError,
    RAGPipelineValidationError,
)

from backend.services.llm_service import LLMService
from backend.services.embedding_service import EmbeddingService
from backend.services.retrieval_service import RetrievalService
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

rag_pipeline: RAGPipeline | None = None


def get_rag_pipeline() -> RAGPipeline:
    """Lazily initialize RAG services so app startup does not load embedding models."""

    global rag_pipeline
    if rag_pipeline is None:
        embedding_service = EmbeddingService()
        vectordb_service = VectorDBService()
        retrieval_service = RetrievalService(
            embedding_service=embedding_service,
            vectordb_service=vectordb_service,
        )
        rag_pipeline = RAGPipeline(
            retrieval_service=retrieval_service,
            llm_service=LLMService(),
        )

    return rag_pipeline


# -----------------------------
# Ask Endpoint
# -----------------------------

@router.post(
    "/ask",
    summary="Retrieve Relevant Industrial Knowledge",
    description=(
        "Accepts a user question, embeds it with the existing embedding service, "
        "searches the ChromaDB knowledge base, and generates a grounded Gemini answer."
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
        response = get_rag_pipeline().ask(
            question=request.question,
            top_k=request.top_k,
        )
    except RAGPipelineValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RAGPipelineRetrievalError as exc:
        logger.exception("Retrieval failed for question.")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve relevant chunks.",
        ) from exc
    except RAGPipelineGenerationError as exc:
        logger.exception("Answer generation failed for question.")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate an answer.",
        ) from exc

    total_time_ms = int((perf_counter() - start_time) * 1000)
    logger.info(
        "Ask request completed: top_k=%s sources=%s total_latency_ms=%s",
        request.top_k,
        len(response["sources"]),
        total_time_ms,
    )

    return {
        "success": True,
        "question": response["question"],
        "answer": response["answer"],
        "model": response["model"],
        "retrieval_time_ms": total_time_ms,
        "total_results": len(response["retrieval"]["results"]),
        "sources": response["sources"],
    }
