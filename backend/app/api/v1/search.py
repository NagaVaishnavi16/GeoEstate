"""HTTP adapter for the shared property search service."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_property_search_service
from app.schemas.property import PropertyListResponse, PropertySearchRequest
from app.services.search import PropertySearchService
from app.services.search_types import PropertySearchCriteria

router = APIRouter(tags=["search"])


@router.post("/search", response_model=PropertyListResponse, summary="Search properties")
async def search_properties(
    request: PropertySearchRequest,
    service: Annotated[PropertySearchService, Depends(get_property_search_service)],
) -> PropertyListResponse:
    """Translate a validated API request into the reusable search-service contract."""
    criteria = PropertySearchCriteria(**request.model_dump())
    properties, total = await service.search(criteria)
    return PropertyListResponse(items=properties, total=total, limit=criteria.limit, offset=criteria.offset)
