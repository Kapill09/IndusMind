import logging
from time import perf_counter
from typing import Any

from fastapi import APIRouter, HTTPException, status, Query

from backend.services.knowledge_graph_service import KnowledgeGraphService, KnowledgeGraphServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])
knowledge_graph_service = KnowledgeGraphService()


@router.get("", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def get_knowledge_graph(document_ids: list[str] | None = Query(default=None)) -> dict[str, Any]:
    """Return the knowledge graph as JSON for the frontend visualization layer."""

    started_at = perf_counter()
    logger.info("Entering knowledge graph endpoint")
    try:
        graph = knowledge_graph_service.build_graph(document_ids=document_ids)
        nodes = graph.get("nodes") or []
        edges = graph.get("edges") or []
        logger.info("Knowledge graph node count: %s", len(nodes))
        logger.info("Knowledge graph edge count: %s", len(edges))
        logger.info(
            "Leaving knowledge graph endpoint: execution_time_ms=%s",
            int((perf_counter() - started_at) * 1000),
        )
        return {
            "nodes": nodes,
            "edges": edges,
        }
    except KnowledgeGraphServiceError as exc:
        logger.exception(
            "Failed to build knowledge graph after %sms",
            int((perf_counter() - started_at) * 1000),
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
