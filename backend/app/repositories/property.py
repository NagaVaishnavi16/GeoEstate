"""Async SQLAlchemy repository for property persistence operations."""

from decimal import Decimal
from typing import List

from sqlalchemy import Float, and_, cast, distinct, func, or_, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.models.locality_statistics import LocalityStatistics
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.services.search_types import (
    PropertySearchCriteria,
    PropertySortField,
    SortOrder,
)


class PropertyRepository:
    """Encapsulate all SQLAlchemy queries for the Property aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_properties(
        self, *, limit: int, offset: int
    ) -> tuple[List[Property], int]:
        """Return an ordered page of properties and the matching total count."""
        total = await self._session.scalar(
            select(func.count()).select_from(Property)
        )

        result = await self._session.scalars(
            select(Property)
            .order_by(Property.location, Property.property_id)
            .limit(limit)
            .offset(offset)
        )

        return list(result), total or 0

    async def get_by_id(self, property_id: str) -> Property | None:
        """Return one property by its stable external identifier."""
        return await self._session.get(Property, property_id)

    async def list_distinct_locations(self) -> List[str]:
        """Return every unique locality represented in imported property records."""
        result = await self._session.scalars(
            select(distinct(Property.location)).order_by(Property.location)
        )
        return list(result)

    async def set_coordinates_for_location(
        self,
        locality: str,
        latitude: Decimal,
        longitude: Decimal,
    ) -> int:
        """Compatibility wrapper that retains non-destructive coordinate semantics."""
        return await self.fill_missing_coordinates_for_location(locality, latitude, longitude)

    async def list_missing_coordinate_batch(
        self,
        *,
        after_property_id: str | None,
        batch_size: int,
    ) -> List[Property]:
        """Return one deterministic batch that still needs either coordinate value."""
        filters = [or_(Property.latitude.is_(None), Property.longitude.is_(None))]
        if after_property_id is not None:
            filters.append(Property.property_id > after_property_id)
        result = await self._session.scalars(
            select(Property)
            .where(*filters)
            .order_by(Property.property_id)
            .limit(batch_size)
        )
        return list(result)

    async def coordinate_coverage_counts(self) -> tuple[int, int]:
        """Return the total property count and count with complete coordinates."""
        total = await self._session.scalar(select(func.count()).select_from(Property))
        geocoded = await self._session.scalar(
            select(func.count())
            .select_from(Property)
            .where(Property.latitude.is_not(None), Property.longitude.is_not(None))
        )
        return total or 0, geocoded or 0

    async def list_remaining_coordinate_localities(self) -> list[tuple[str, int]]:
        """Return remaining coordinate gaps grouped by locality for coverage reporting."""
        result = await self._session.execute(
            select(Property.location, func.count().label("property_count"))
            .where(or_(Property.latitude.is_(None), Property.longitude.is_(None)))
            .group_by(Property.location)
            .order_by(func.count().desc(), Property.location.asc())
        )
        return [(location, count) for location, count in result.all()]

    async def fill_missing_coordinates_for_location(
        self,
        locality: str,
        latitude: Decimal,
        longitude: Decimal,
    ) -> int:
        """Fill only null coordinates for a locality; preserve existing valid values."""
        result = await self._session.execute(
            update(Property)
            .where(
                Property.location == locality,
                or_(Property.latitude.is_(None), Property.longitude.is_(None)),
            )
            .values(
                latitude=func.coalesce(Property.latitude, latitude),
                longitude=func.coalesce(Property.longitude, longitude),
            )
        )
        return result.rowcount or 0

    async def list_missing_geometry_batch(
        self,
        *,
        after_property_id: str | None,
        batch_size: int,
    ) -> List[Property]:
        """Return coordinate-complete properties whose geometry trigger result is absent."""
        filters = [
            Property.geometry.is_(None),
            Property.latitude.is_not(None),
            Property.longitude.is_not(None),
        ]
        if after_property_id is not None:
            filters.append(Property.property_id > after_property_id)
        result = await self._session.scalars(
            select(Property)
            .where(and_(*filters))
            .order_by(Property.property_id)
            .limit(batch_size)
        )
        return list(result)

    async def list_missing_nearby_place_batch(
        self,
        *,
        after_property_id: str | None,
        batch_size: int,
    ) -> List[Property]:
        """Return coordinate-complete records missing one or more nearby-place fields."""
        filters = [
            Property.latitude.is_not(None),
            Property.longitude.is_not(None),
            or_(
                Property.nearest_metro.is_(None),
                Property.nearest_hospital.is_(None),
                Property.nearest_school.is_(None),
                Property.nearest_park.is_(None),
                Property.nearest_metro_distance_m.is_(None),
                Property.nearest_hospital_distance_m.is_(None),
                Property.nearest_school_distance_m.is_(None),
                Property.nearest_park_distance_m.is_(None),
                Property.nearby_park_count.is_(None),
            ),
        ]
        if after_property_id is not None:
            filters.append(Property.property_id > after_property_id)
        result = await self._session.scalars(
            select(Property).where(and_(*filters)).order_by(Property.property_id).limit(batch_size)
        )
        return list(result)

    async def list_missing_nearby_places_for_coordinates(
        self,
        coordinates: tuple[tuple[Decimal, Decimal], ...],
    ) -> list[Property]:
        """Return only requested coordinate-complete records that still need nearby facts."""
        if not coordinates:
            return []
        return list(
            await self._session.scalars(
                select(Property)
                .where(
                    tuple_(Property.latitude, Property.longitude).in_(coordinates),
                    or_(
                        Property.nearest_metro.is_(None),
                        Property.nearest_hospital.is_(None),
                        Property.nearest_school.is_(None),
                        Property.nearest_park.is_(None),
                        Property.nearest_metro_distance_m.is_(None),
                        Property.nearest_hospital_distance_m.is_(None),
                        Property.nearest_school_distance_m.is_(None),
                        Property.nearest_park_distance_m.is_(None),
                        Property.nearby_park_count.is_(None),
                    ),
                )
                .order_by(Property.property_id)
            )
        )

    async def list_missing_score_batch(
        self,
        *,
        after_property_id: str | None,
        batch_size: int,
    ) -> list[tuple[Property, Decimal | None, Decimal | None]]:
        """Return properties needing a score with their exact-locality SQL benchmarks."""
        filters = [
            or_(
                Property.investment_score.is_(None),
                Property.connectivity_score.is_(None),
                Property.green_score.is_(None),
                Property.liveability_score.is_(None),
            )
        ]
        if after_property_id is not None:
            filters.append(Property.property_id > after_property_id)
        result = await self._session.execute(
            select(
                Property,
                LocalityStatistics.average_price_per_sqft,
                LocalityStatistics.average_built_up_area_sqft,
            )
            .outerjoin(LocalityStatistics, Property.location == LocalityStatistics.locality)
            .where(*filters)
            .order_by(Property.property_id)
            .limit(batch_size)
        )
        return [
            (property_record, average_rate, average_area)
            for property_record, average_rate, average_area in result.all()
        ]

    async def fill_missing_scores(
        self,
        property_id: str,
        *,
        investment_score: Decimal | None,
        connectivity_score: Decimal | None,
        green_score: Decimal | None,
        liveability_score: Decimal | None,
    ) -> int:
        """Fill computed score gaps without overwriting an existing persisted score."""
        supplied_values = {
            "investment_score": investment_score,
            "connectivity_score": connectivity_score,
            "green_score": green_score,
            "liveability_score": liveability_score,
        }
        missing_targets = [
            getattr(Property, name).is_(None)
            for name, value in supplied_values.items()
            if value is not None
        ]
        if not missing_targets:
            return 0
        values = {
            name: func.coalesce(getattr(Property, name), value)
            for name, value in supplied_values.items()
            if value is not None
        }
        result = await self._session.execute(
            update(Property)
            .where(Property.property_id == property_id, or_(*missing_targets))
            .values(**values)
        )
        return result.rowcount or 0

    async def fill_missing_nearby_places(
        self,
        property_id: str,
        *,
        nearest_metro: str | None,
        nearest_metro_distance_m: int | None,
        nearest_hospital: str | None,
        nearest_hospital_distance_m: int | None,
        nearest_school: str | None,
        nearest_school_distance_m: int | None,
        nearest_park: str | None,
        nearest_park_distance_m: int | None,
        nearby_park_count: int | None,
    ) -> int:
        """Fill supplied nearby-place values only where the corresponding column is null."""
        supplied_values = {
            "nearest_metro": nearest_metro,
            "nearest_metro_distance_m": nearest_metro_distance_m,
            "nearest_hospital": nearest_hospital,
            "nearest_hospital_distance_m": nearest_hospital_distance_m,
            "nearest_school": nearest_school,
            "nearest_school_distance_m": nearest_school_distance_m,
            "nearest_park": nearest_park,
            "nearest_park_distance_m": nearest_park_distance_m,
            "nearby_park_count": nearby_park_count,
        }
        missing_targets = [
            getattr(Property, name).is_(None)
            for name, value in supplied_values.items()
            if value is not None
        ]
        if not missing_targets:
            return 0
        values = {
            name: func.coalesce(getattr(Property, name), value)
            for name, value in supplied_values.items()
            if value is not None
        }
        result = await self._session.execute(
            update(Property)
            .where(Property.property_id == property_id, or_(*missing_targets))
            .values(**values)
        )
        return result.rowcount or 0

    async def repair_missing_geometry(self, property_ids: list[str]) -> int:
        """Regenerate geometry only where it is null and coordinate inputs are valid."""
        if not property_ids:
            return 0
        result = await self._session.execute(
            update(Property)
            .where(
                Property.property_id.in_(property_ids),
                Property.geometry.is_(None),
                Property.latitude.is_not(None),
                Property.longitude.is_not(None),
            )
            .values(
                geometry=func.ST_SetSRID(
                    func.ST_MakePoint(
                        cast(Property.longitude, Float),
                        cast(Property.latitude, Float),
                    ),
                    4326,
                )
            )
        )
        return result.rowcount or 0

    async def search(
        self,
        criteria: PropertySearchCriteria,
    ) -> tuple[List[Property], int]:
        """Execute a safe, indexed filter query using only whitelisted sort fields."""

        filters = []

        if criteria.location:
            filters.append(
                Property.location.ilike(f"%{criteria.location.strip()}%")
            )

        if criteria.min_price is not None:
            filters.append(
                Property.price_lakh >= criteria.min_price / Decimal("100000")
            )

        if criteria.max_price is not None:
            filters.append(
                Property.price_lakh <= criteria.max_price / Decimal("100000")
            )

        if criteria.bedrooms is not None:
            filters.append(Property.bedrooms == criteria.bedrooms)

        if criteria.min_area is not None:
            filters.append(Property.area_sqft >= criteria.min_area)

        if criteria.max_area is not None:
            filters.append(Property.area_sqft <= criteria.max_area)

        if criteria.property_type:
            filters.append(Property.title.ilike(f"%{criteria.property_type.strip()}%"))

        if criteria.building_status:
            filters.append(
                func.lower(Property.building_status) == criteria.building_status.strip().casefold()
            )

        if criteria.near_metro:
            # Proximity is established by the computed distance. The OSM display name is
            # optional metadata and must not exclude a verified metro-distance result.
            filters.append(Property.nearest_metro_distance_m.is_not(None))

        if criteria.near_hospital:
            filters.append(Property.nearest_hospital.is_not(None))

        if criteria.near_school:
            filters.append(Property.nearest_school.is_not(None))

        if criteria.near_park:
            filters.append(Property.nearest_park.is_not(None))

        sort_columns = {
            PropertySortField.PRICE: Property.price_lakh,
            PropertySortField.AREA: Property.area_sqft,
            PropertySortField.BEDROOMS: Property.bedrooms,
            PropertySortField.LOCATION: Property.location,
        }

        sort_column = sort_columns[criteria.sort_by]

        order_by = (
            sort_column.desc()
            if criteria.sort_order is SortOrder.DESC
            else sort_column.asc()
        )

        count_statement = (
            select(func.count())
            .select_from(Property)
            .where(*filters)
        )

        data_statement = (
            select(Property)
            .where(*filters)
            .order_by(order_by, Property.property_id.asc())
            .limit(criteria.limit)
            .offset(criteria.offset)
        )

        total = await self._session.scalar(count_statement)
        properties = list(await self._session.scalars(data_statement))

        return properties, total or 0

    async def create(self, payload: PropertyCreate) -> Property:
        """Stage a validated property for insertion within the caller's transaction."""
        property_record = Property(**payload.model_dump())
        self._session.add(property_record)
        await self._session.flush()
        await self._session.refresh(property_record)
        return property_record

    async def update(
        self,
        property_record: Property,
        payload: PropertyUpdate,
    ) -> Property:
        """Apply supplied mutable fields within the caller's transaction."""

        for field_name, value in payload.model_dump(exclude_unset=True).items():
            setattr(property_record, field_name, value)

        await self._session.flush()
        await self._session.refresh(property_record)

        return property_record

    async def delete(self, property_record: Property) -> None:
        """Stage a property deletion within the caller's transaction."""
        await self._session.delete(property_record)
        await self._session.flush()
