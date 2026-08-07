"""HTTP adapter for AI-assisted, validated natural-language property search."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_natural_language_search_service
from app.schemas.natural_search import NaturalSearchRequest, NaturalSearchResponse
from app.services.natural_language_search import NaturalLanguageSearchService

router = APIRouter(prefix="/api/v1/search", tags=["natural-search"])


@router.post(
    "/natural",
    response_model=NaturalSearchResponse,
    summary="Search properties using natural language",
    description=(
        "Gemini extracts JSON filters only. The filters must pass Pydantic validation before "
        "the existing property search service is called."
    ),
)
async def natural_language_search(
    request: NaturalSearchRequest,
    service: Annotated[NaturalLanguageSearchService, Depends(get_natural_language_search_service)],
) -> NaturalSearchResponse:
    """Extract validated filters with Gemini, then execute only through the existing search service."""
    return await service.search(query=request.query, limit=request.limit, offset=request.offset)
