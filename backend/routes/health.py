import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.services.health_service import HealthService, HealthServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])
health_service = HealthService()


@router.get("", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def get_health() -> dict[str, Any]:
    """Return the health status for the backend knowledge pipeline."""

    try:
        return health_service.get_health()
    except HealthServiceError as exc:
        logger.exception("Failed to compute backend health")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
