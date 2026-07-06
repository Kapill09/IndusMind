import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from backend.services.analytics_service import AnalyticsService, AnalyticsServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])
analytics_service = AnalyticsService()


@router.get("", response_model=dict[str, Any], status_code=status.HTTP_200_OK)
def get_analytics() -> dict[str, Any]:
    """Return aggregate analytics for the indexed knowledge base."""

    try:
        return analytics_service.get_analytics()
    except AnalyticsServiceError as exc:
        logger.exception("Failed to compute analytics")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
