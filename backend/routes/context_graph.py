"""API route for the answer-scoped Context Knowledge Graph."""

import logging
from time import perf_counter
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.services.context_graph_service import (
    ContextGraphService,
    ContextGraphServiceError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Context Graph"])
context_graph_service = ContextGraphService()


class ContextGraphSource(BaseModel):
    """Mirrors the source shape returned by ``/api/ask``."""

    chunk_id: str = ""
    text: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextGraphEntity(BaseModel):
    """Entity label + type pair from the ask response."""

    label: str = ""
    type: str = ""


class ContextGraphRequest(BaseModel):
    """Request body for ``POST /api/context-graph``."""

    question: str = Field(..., min_length=1, description="The original user question.")
    sources: list[ContextGraphSource] = Field(default_factory=list)
    entities: list[ContextGraphEntity] = Field(default_factory=list)
    answer: str = Field(default="", description="The generated answer text.")


@router.post(
    "/context-graph",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Build an answer-scoped context graph",
    description=(
        "Accepts the sources and entities from an /api/ask response and "
        "constructs a temporary knowledge graph that visualises only the "
        "knowledge used to produce the answer."
    ),
)
def build_context_graph(request: ContextGraphRequest) -> dict[str, Any]:
    """Build a context graph scoped to the RAG answer."""

    started_at = perf_counter()
    logger.info("Context graph request: question=%s sources=%s entities=%s",
                request.question[:80], len(request.sources), len(request.entities))

    try:
        graph = context_graph_service.build_context_graph(
            question=request.question,
            sources=[s.model_dump() for s in request.sources],
            entities=[e.model_dump() for e in request.entities],
            answer=request.answer,
        )
    except ContextGraphServiceError as exc:
        logger.exception("Context graph construction failed after %sms",
                         int((perf_counter() - started_at) * 1000))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    logger.info(
        "Context graph built: nodes=%s edges=%s latency_ms=%s",
        graph["stats"]["totalNodes"],
        graph["stats"]["totalEdges"],
        int((perf_counter() - started_at) * 1000),
    )
    return graph
