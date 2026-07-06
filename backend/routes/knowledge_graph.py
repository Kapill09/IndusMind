import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.services.knowledge_graph_service import KnowledgeGraphService, KnowledgeGraphServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge-graph"])
knowledge_graph_service = KnowledgeGraphService()


@router.get("", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def get_knowledge_graph() -> dict[str, Any]:
    """Return the knowledge graph as JSON for the frontend visualization layer."""

    try:
        return knowledge_graph_service.build_graph()
    except KnowledgeGraphServiceError as exc:
        logger.exception("Failed to build knowledge graph")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
