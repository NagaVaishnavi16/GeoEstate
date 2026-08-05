"""Public read-only HTTP endpoints for property listings."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.dependencies import get_property_service
from app.schemas.property import (
    CoordinatesResponse,
    FutureIntelligenceResponse,
    PropertyDetailsResponse,
    PropertyListResponse,
    PropertyResponse,
)
from app.services.property import PropertyService

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=PropertyListResponse, summary="List properties")
async def list_properties(
    service: Annotated[PropertyService, Depends(get_property_service)],
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum listings to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Number of listings to skip")] = 0,
) -> PropertyListResponse:
    """Return a deterministic, offset-paginated property listing."""
    properties, total = await service.list_properties(limit=limit, offset=offset)
    return PropertyListResponse(items=properties, total=total, limit=limit, offset=offset)


@router.get("/{property_id}/details", response_model=PropertyDetailsResponse, summary="Get rich property details")
async def get_property_details(
    property_id: Annotated[str, Path(min_length=1, max_length=24)],
    service: Annotated[PropertyService, Depends(get_property_service)],
) -> PropertyDetailsResponse:
    """Return a stable, extensible detail shape without adding intelligence logic yet."""
    property_record = await service.get_property_details(property_id)
    if property_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return PropertyDetailsResponse(
        property=property_record,
        coordinates=CoordinatesResponse(latitude=property_record.latitude, longitude=property_record.longitude),
        future_intelligence=FutureIntelligenceResponse(
            investment_score=property_record.investment_score,
            ai_summary=property_record.ai_summary,
            nearest_school=property_record.nearest_school,
            nearest_hospital=property_record.nearest_hospital,
            nearest_metro=property_record.nearest_metro,
            nearest_park=property_record.nearest_park,
            nearest_metro_distance_m=property_record.nearest_metro_distance_m,
            nearest_hospital_distance_m=property_record.nearest_hospital_distance_m,
            nearest_school_distance_m=property_record.nearest_school_distance_m,
            nearest_park_distance_m=property_record.nearest_park_distance_m,
            nearby_park_count=property_record.nearby_park_count,
            green_score=property_record.green_score,
            satellite_analysis=None,
        ),
    )


@router.get("/{property_id}", response_model=PropertyResponse, summary="Get a property")
async def get_property(
    property_id: Annotated[str, Path(min_length=1, max_length=24)],
    service: Annotated[PropertyService, Depends(get_property_service)],
) -> PropertyResponse:
    """Return one property by its stable `hyd-...` external identifier."""
    property_record = await service.get_property(property_id)
    if property_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return property_record
