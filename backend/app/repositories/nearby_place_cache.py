"""SQLAlchemy persistence operations for the Overpass nearby-place cache."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.nearby_place_cache import NearbyPlaceCache


class NearbyPlaceCacheRepository:
    """Encapsulate durable nearby-place cache lookup and persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, coordinate_bucket: str, category: str) -> NearbyPlaceCache | None:
        """Return one cached provider outcome for a bucket and place category."""
        return await self._session.get(NearbyPlaceCache, (coordinate_bucket, category))

    async def save(self, cache_entry: NearbyPlaceCache) -> NearbyPlaceCache:
        """Stage a new or updated provider result for the current transaction."""
        self._session.add(cache_entry)
        await self._session.flush()
        return cache_entry
