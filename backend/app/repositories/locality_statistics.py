"""Read-only database queries for locality-level intelligence."""
from __future__ import annotations
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.locality_statistics import LocalityStatistics


class LocalityStatisticsRepository:
    """Keep PostgreSQL locality aggregation queries out of the API and service layers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_localities(self, *, limit: int, offset: int) -> tuple[list[LocalityStatistics], int]:
        """Return a deterministic page of locality analytics and the matching total."""
        total = await self._session.scalar(select(func.count()).select_from(LocalityStatistics))
        records = await self._session.scalars(
            select(LocalityStatistics)
            .order_by(LocalityStatistics.locality.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(records), total or 0

    async def get_by_locality(self, locality: str) -> LocalityStatistics | None:
        """Resolve one locality case-insensitively without substring ambiguity."""
        return await self._session.scalar(
            select(LocalityStatistics).where(
                func.lower(LocalityStatistics.locality) == locality.strip().casefold()
            )
        )

    async def list_by_average_price(
        self,
        *,
        descending: bool,
        limit: int,
    ) -> list[LocalityStatistics]:
        """Return localities ordered by database-computed average listing price."""
        order = (
            LocalityStatistics.average_price_lakh.desc()
            if descending
            else LocalityStatistics.average_price_lakh.asc()
        )
        records = await self._session.scalars(
            select(LocalityStatistics)
            .order_by(order, LocalityStatistics.locality.asc())
            .limit(limit)
        )
        return list(records)
