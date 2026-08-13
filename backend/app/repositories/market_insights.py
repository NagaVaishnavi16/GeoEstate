"""SQL-only descriptive analytics queries for the existing property dataset."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.locality_statistics import LocalityStatistics
from app.models.property import Property


class MarketInsightsRepository:
    """Own database aggregation queries used by the frontend insights layer."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def price_distribution(self) -> tuple[int, Decimal | None, Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
        """Return price-per-square-foot quantiles for records that have that source field."""
        statement = select(
            func.count(Property.property_id),
            func.min(Property.rate_per_sqft),
            func.percentile_cont(0.25).within_group(Property.rate_per_sqft),
            func.percentile_cont(0.5).within_group(Property.rate_per_sqft),
            func.percentile_cont(0.75).within_group(Property.rate_per_sqft),
            func.max(Property.rate_per_sqft),
        ).where(Property.rate_per_sqft.is_not(None))
        row = (await self._session.execute(statement)).one()
        return tuple(row)

    async def locality_price_metrics(self, *, limit: int) -> list[LocalityStatistics]:
        """Return the highest-rate sufficiently represented localities."""
        result = await self._session.scalars(
            select(LocalityStatistics)
            .where(LocalityStatistics.average_price_per_sqft.is_not(None), LocalityStatistics.total_listings >= 3)
            .order_by(LocalityStatistics.average_price_per_sqft.desc(), LocalityStatistics.locality.asc())
            .limit(limit)
        )
        return list(result)

    async def score_price_metrics(self) -> list[tuple[str, int, Decimal | None, Decimal | None, Decimal | None]]:
        """Aggregate each available deterministic score against current listing prices."""
        metrics: list[tuple[str, int, Decimal | None, Decimal | None, Decimal | None]] = []
        for label, column in (
            ("Investment", Property.investment_score),
            ("Connectivity", Property.connectivity_score),
            ("Green", Property.green_score),
            ("Liveability", Property.liveability_score),
        ):
            row = (
                await self._session.execute(
                    select(
                        func.count(Property.property_id),
                        func.avg(column),
                        func.avg(Property.price_lakh),
                        func.avg(Property.rate_per_sqft),
                    ).where(column.is_not(None))
                )
            ).one()
            metrics.append((label, *row))
        return metrics

    async def rate_outliers(self, *, limit: int) -> list[tuple[Property, Decimal, Decimal]]:
        """Return largest absolute rate deviations versus the listing's locality average."""
        ratio = Property.rate_per_sqft / LocalityStatistics.average_price_per_sqft
        result = await self._session.execute(
            select(Property, LocalityStatistics.average_price_per_sqft, ratio.label("rate_ratio"))
            .join(LocalityStatistics, LocalityStatistics.locality == Property.location)
            .where(
                Property.rate_per_sqft.is_not(None),
                Property.rate_per_sqft > 0,
                LocalityStatistics.average_price_per_sqft.is_not(None),
                LocalityStatistics.average_price_per_sqft > 0,
            )
            .order_by(func.abs(ratio - 1).desc(), Property.property_id.asc())
            .limit(limit)
        )
        return list(result.all())

    async def amenity_price_metrics(self) -> list[tuple[str, int, Decimal | None, Decimal | None, Decimal | None]]:
        """Summarize listings with verified distances; null never means amenity absence."""
        metrics: list[tuple[str, int, Decimal | None, Decimal | None, Decimal | None]] = []
        for label, column in (
            ("Metro", Property.nearest_metro_distance_m),
            ("Hospital", Property.nearest_hospital_distance_m),
            ("School", Property.nearest_school_distance_m),
            ("Park", Property.nearest_park_distance_m),
        ):
            row = (
                await self._session.execute(
                    select(
                        func.count(Property.property_id),
                        func.avg(Property.price_lakh),
                        func.avg(Property.rate_per_sqft),
                        func.avg(column),
                    ).where(column.is_not(None))
                )
            ).one()
            metrics.append((label, *row))
        return metrics
