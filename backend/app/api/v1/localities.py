"""Read-only HTTP adapters for current locality intelligence."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.dependencies import get_locality_intelligence_service
from app.models.locality_statistics import LocalityStatistics
from app.schemas.locality import (
    LocalityEnrichmentResponse,
    LocalityListResponse,
    LocalityStatisticsResponse,
)
from app.services.locality_intelligence import LocalityIntelligenceService

router = APIRouter(prefix="/api/v1/localities", tags=["localities"])


def to_response(record: LocalityStatistics) -> LocalityStatisticsResponse:
    """Map the view model into a stable API response with nested enrichment facts."""
    return LocalityStatisticsResponse(
        locality=record.locality,
        total_listings=record.total_listings,
        average_price_lakh=record.average_price_lakh,
        median_price_lakh=record.median_price_lakh,
        minimum_price_lakh=record.minimum_price_lakh,
        maximum_price_lakh=record.maximum_price_lakh,
        average_built_up_area_sqft=record.average_built_up_area_sqft,
        average_price_per_sqft=record.average_price_per_sqft,
        centroid_latitude=record.centroid_latitude,
        centroid_longitude=record.centroid_longitude,
        enrichment=LocalityEnrichmentResponse(
            metro_available_listings=record.metro_available_listings,
            hospital_available_listings=record.hospital_available_listings,
            school_available_listings=record.school_available_listings,
            park_available_listings=record.park_available_listings,
            average_metro_distance_m=record.average_metro_distance_m,
            average_hospital_distance_m=record.average_hospital_distance_m,
            average_school_distance_m=record.average_school_distance_m,
            average_park_distance_m=record.average_park_distance_m,
            average_nearby_park_count=record.average_nearby_park_count,
            average_investment_score=record.average_investment_score,
            average_connectivity_score=record.average_connectivity_score,
            average_green_score=record.average_green_score,
            average_liveability_score=record.average_liveability_score,
        ),
    )


@router.get("", response_model=LocalityListResponse, summary="List locality intelligence")
async def list_localities(
    service: Annotated[LocalityIntelligenceService, Depends(get_locality_intelligence_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> LocalityListResponse:
    """Return a deterministic page of locality-level analytics."""
    records, total = await service.list_localities(limit=limit, offset=offset)
    return LocalityListResponse(items=[to_response(record) for record in records], total=total, limit=limit, offset=offset)


@router.get("/top-expensive", response_model=list[LocalityStatisticsResponse], summary="Most expensive localities")
async def top_expensive_localities(
    service: Annotated[LocalityIntelligenceService, Depends(get_locality_intelligence_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[LocalityStatisticsResponse]:
    """Return localities ordered by descending average listing price."""
    return [to_response(record) for record in await service.top_expensive(limit=limit)]


@router.get("/most-affordable", response_model=list[LocalityStatisticsResponse], summary="Most affordable localities")
async def most_affordable_localities(
    service: Annotated[LocalityIntelligenceService, Depends(get_locality_intelligence_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[LocalityStatisticsResponse]:
    """Return localities ordered by ascending average listing price."""
    return [to_response(record) for record in await service.most_affordable(limit=limit)]


@router.get("/{locality}", response_model=LocalityStatisticsResponse, summary="Get locality intelligence")
async def get_locality(
    locality: Annotated[str, Path(min_length=1, max_length=255)],
    service: Annotated[LocalityIntelligenceService, Depends(get_locality_intelligence_service)],
) -> LocalityStatisticsResponse:
    """Return exact case-insensitive analytics for one locality."""
    record = await service.get_locality(locality)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Locality not found")
    return to_response(record)
