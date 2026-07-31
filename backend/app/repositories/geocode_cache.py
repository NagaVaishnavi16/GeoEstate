"""SQLAlchemy persistence operations for locality geocoding cache entries."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geocode_cache import GeocodeCache


class GeocodeCacheRepository:
    """Encapsulate durable cache lookup and insertion operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, location_key: str) -> GeocodeCache | None:
        """Return a cached success, miss, or failure for one normalized locality."""
        return await self._session.get(GeocodeCache, location_key)

    async def get_many(self, location_keys: list[str]) -> dict[str, GeocodeCache]:
        """Return cache rows indexed by normalized locality key."""
        if not location_keys:
            return {}
        rows = await self._session.scalars(
            select(GeocodeCache).where(GeocodeCache.location_key.in_(location_keys))
        )
        return {entry.location_key: entry for entry in rows}

    async def add(self, cache_entry: GeocodeCache) -> GeocodeCache:
        """Stage a newly resolved cache entry for durable storage."""
        self._session.add(cache_entry)
        await self._session.flush()
        return cache_entry

    async def save(self, cache_entry: GeocodeCache) -> GeocodeCache:
        """Persist either a new cache entry or updated diagnostics for an existing one."""
        self._session.add(cache_entry)
        await self._session.flush()
        return cache_entry
