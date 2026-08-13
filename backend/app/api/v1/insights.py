"""Read-only descriptive market analytics endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_market_insights_service
from app.schemas.insights import MarketInsightsResponse
from app.services.market_insights import MarketInsightsService

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


@router.get("", response_model=MarketInsightsResponse, summary="Get descriptive market insights")
async def get_market_insights(
    service: Annotated[MarketInsightsService, Depends(get_market_insights_service)],
) -> MarketInsightsResponse:
    """Return current SQL-backed descriptive metrics; no returns or causal claims are made."""
    return await service.get_insights()
