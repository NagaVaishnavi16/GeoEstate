"""Transport-independent locality intelligence use cases."""

import logging

from app.models.locality_statistics import LocalityStatistics
from app.repositories.locality_statistics import LocalityStatisticsRepository

LOGGER = logging.getLogger(__name__)


class LocalityIntelligenceService:
    """Expose current PostgreSQL/PostGIS locality analytics to any future caller."""

    def __init__(self, repository: LocalityStatisticsRepository) -> None:
        self._repository = repository

    async def list_localities(self, *, limit: int, offset: int) -> tuple[list[LocalityStatistics], int]:
        """Return an ordered page of locality intelligence records."""
        records, total = await self._repository.list(limit=limit, offset=offset)
        LOGGER.info("locality_intelligence_listed result_count=%d total=%d", len(records), total)
        return records, total

    async def get_locality(self, locality: str) -> LocalityStatistics | None:
        """Return one exact locality analytics record."""
        return await self._repository.get_by_locality(locality)

    async def top_expensive(self, *, limit: int) -> list[LocalityStatistics]:
        """Return localities ordered from highest to lowest average price."""
        return await self._repository.list_by_average_price(descending=True, limit=limit)

    async def most_affordable(self, *, limit: int) -> list[LocalityStatistics]:
        """Return localities ordered from lowest to highest average price."""
        return await self._repository.list_by_average_price(descending=False, limit=limit)
