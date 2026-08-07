"""Natural-language search orchestration that reuses the canonical search service."""

import logging

from app.schemas.natural_search import (
    ExtractedPropertyFilters,
    NaturalSearchClarificationResponse,
    NaturalSearchResponse,
    NaturalSearchSuccessResponse,
    NaturalSearchValidationResponse,
)
from app.services.gemini_parser import IntentParser, ParserFailure
from app.services.search import PropertySearchService
from app.services.search_types import PropertySearchCriteria

LOGGER = logging.getLogger(__name__)


class NaturalLanguageSearchService:
    """Translate validated AI intent into the existing repository-backed search use case."""

    def __init__(self, parser: IntentParser, search_service: PropertySearchService) -> None:
        self._parser = parser
        self._search_service = search_service

    async def search(self, *, query: str, limit: int, offset: int) -> NaturalSearchResponse:
        """Parse, validate, clarify, or execute exclusively through PropertySearchService."""
        parsed = await self._parser.parse(query)
        if isinstance(parsed, ParserFailure):
            return NaturalSearchValidationResponse(message=parsed.message, errors=parsed.errors)
        if parsed.needs_clarification:
            return NaturalSearchClarificationResponse(
                message=parsed.clarification_message or "Please clarify your search.",
                missing_fields=parsed.missing_fields,
            )
        if not self._has_actionable_filter(parsed):
            return NaturalSearchClarificationResponse(
                message="Please provide a locality, budget, property type, size, bedroom count, or nearby-place preference.",
                missing_fields=["search_criteria"],
            )

        criteria = self._to_search_criteria(parsed, limit=limit, offset=offset)
        properties, total = await self._search_service.search(criteria)
        LOGGER.info("natural_language_search_complete total=%d locality=%s", total, parsed.locality)
        return NaturalSearchSuccessResponse(
            query=query,
            extracted_filters=parsed,
            results=properties,
            total_results=total,
        )

    @staticmethod
    def _to_search_criteria(
        filters: ExtractedPropertyFilters,
        *,
        limit: int,
        offset: int,
    ) -> PropertySearchCriteria:
        """Map only validated intent fields into the existing shared search contract."""
        return PropertySearchCriteria(
            location=filters.locality,
            min_price=filters.price_min,
            max_price=filters.price_max,
            bedrooms=filters.bhk,
            min_area=filters.area_min,
            max_area=filters.area_max,
            property_type=filters.property_type,
            building_status=filters.building_status,
            near_metro=filters.nearby.metro,
            near_hospital=filters.nearby.hospital,
            near_school=filters.nearby.school,
            near_park=filters.nearby.park,
            limit=limit,
            offset=offset,
            sort_by=filters.sort_by,
            sort_order=filters.sort_order,
        )

    @staticmethod
    def _has_actionable_filter(filters: ExtractedPropertyFilters) -> bool:
        """Prevent an empty model extraction from becoming an unbounded property query."""
        return any(
            (
                filters.property_type,
                filters.bhk is not None,
                filters.locality,
                filters.price_min is not None,
                filters.price_max is not None,
                filters.area_min is not None,
                filters.area_max is not None,
                filters.building_status,
                filters.nearby.metro,
                filters.nearby.hospital,
                filters.nearby.school,
                filters.nearby.park,
            )
        )
