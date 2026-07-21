import logging
from time import perf_counter

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.pipeline.rag_pipeline import (
    RAGPipeline,
    RAGPipelineGenerationError,
    RAGPipelineRetrievalError,
    RAGPipelineValidationError,
)

from backend.services.document_id_validation import sanitize_document_ids
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

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "question": "What is Problem Statement 8?",
                    "top_k": 5,
                },
                {
                    "question": "Explain the maintenance procedure.",
                    "top_k": 5,
                    "document_ids": ["maintenance_manual_2024"],
                },
            ]
        }
    )

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
    document_ids: list[str] | None = Field(
        default=None,
        description="Optional list of document IDs to restrict retrieval to specific sources.",
    )
    user_role: str = Field(
        default="public",
        description="The access role of the user requesting the information (e.g., 'public', 'engineer', 'admin').",
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
            embedding_service=embedding_service,
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
        pipeline = get_rag_pipeline()
        vdb = pipeline.retrieval_service.vectordb_service
        emb = pipeline.retrieval_service.embedding_service
        
        sanitized_document_ids = sanitize_document_ids(request.document_ids)
        logger.info("=" * 80)
        logger.info("USER QUESTION: %s", request.question)
        logger.info("RAW DOCUMENT IDS: %s", request.document_ids)
        logger.info("SANITIZED DOCUMENT IDS: %s", sanitized_document_ids)
        logger.info("=" * 80)
        q_emb = emb.generate_embedding(request.question)
        
        print("\n======== FASTAPI ========")
        print(f"Raw Request Body: {request.model_dump_json()}")
        print(f"Parsed Request Model: {request}")
        print(f"document_ids: {request.document_ids}")
        print("======== RAG PIPELINE ========")
        print(f"Received document_ids: {sanitized_document_ids}")
        print(f"Generated Chroma Filter: Pending (handled in retrieval service)\n")

        logger.debug(
            "Ask request accepted: question=%s document_ids=%s sanitized_document_ids=%s embedding_dim=%s",
            request.question,
            request.document_ids,
            sanitized_document_ids,
            len(q_emb),
        )
        
        response = pipeline.ask(
                question=request.question,
                top_k=request.top_k,
                document_ids=sanitized_document_ids,
                user_role=request.user_role,
            )
        
        chunks = response["retrieval"]["results"]
        logger.debug("Ask request completed with %s retrieved chunks", len(chunks))
            
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
        "success": response["success"],
        "question": response["question"],
        "answer": response["answer"],
        "model": response["model"],
        "retrieval_time_ms": total_time_ms,
        "total_results": len(response["retrieval"]["results"]),
        "sources": response["sources"],
        "entities": response["entities"],
        "context_chunks": response["context_chunks"],
        "retrieval_scope": response["retrieval_scope"],
        "confidence": response["confidence"],
        "intent": response["intent"],
        "rejection_reason": response.get("rejection_reason"),
        "missing_entities": response.get("missing_entities"),
    }
