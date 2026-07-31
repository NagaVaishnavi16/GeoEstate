"""Shared property search use case for frontend and future AI callers."""

import logging

from app.models.property import Property
from app.repositories.property import PropertyRepository
from app.services.search_types import PropertySearchCriteria

LOGGER = logging.getLogger(__name__)


class PropertySearchService:
    """Coordinate business-level property search without any HTTP dependency."""

    def __init__(self, repository: PropertyRepository) -> None:
        self._repository = repository

    async def search(self, criteria: PropertySearchCriteria) -> tuple[list[Property], int]:
        """Search canonical properties using the same service for all caller types."""
        properties, total = await self._repository.search(criteria)
        LOGGER.info(
            "property_search_complete location=%s bedrooms=%s result_count=%d total=%d",
            criteria.location,
            criteria.bedrooms,
            len(properties),
            total,
        )
        return properties, total
