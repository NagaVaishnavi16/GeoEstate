"""Unit tests for cache-first Overpass nearby-place enrichment."""

import unittest
from decimal import Decimal
from types import SimpleNamespace

from app.services.nearby_places import (
    CategoryNearbyResult,
    NearbyPlace,
    NearbyPlaceService,
    PlaceCategory,
)


class _Settings:
    overpass_park_count_radius_m = 2_000


class _CacheRepository:
    def __init__(self) -> None:
        self.entries: dict[tuple[str, str], object] = {}
        self.saved: list[object] = []

    async def get(self, bucket: str, category: str):
        return self.entries.get((bucket, category))

    async def save(self, entry):
        self.entries[(entry.coordinate_bucket, entry.category)] = entry
        self.saved.append(entry)
        return entry


class _OverpassClient:
    def __init__(self) -> None:
        self.calls: list[PlaceCategory] = []

    async def search_all(self, latitude: Decimal, longitude: Decimal):
        self.calls.append(PlaceCategory.METRO)
        return {
            category: [{"lat": "17.4401", "lon": "78.3501", "tags": self._tags(category)}]
            for category in PlaceCategory
        }

    @staticmethod
    def _tags(category: PlaceCategory) -> dict[str, str]:
        return {
            PlaceCategory.METRO: {"name": "metro place", "railway": "station", "station": "subway"},
            PlaceCategory.HOSPITAL: {"name": "hospital place", "amenity": "hospital"},
            PlaceCategory.SCHOOL: {"name": "school place", "amenity": "school"},
            PlaceCategory.PARK: {"name": "park place", "leisure": "park"},
        }[category]


class NearbyPlaceServiceTests(unittest.IsolatedAsyncioTestCase):
    """Verify parsing, selection, and durable cache reuse without HTTP access."""

    def test_select_nearest_uses_way_center_and_counts_unnamed_parks(self) -> None:
        service = NearbyPlaceService(_CacheRepository(), _OverpassClient(), _Settings())
        result = service.select_nearest(
            PlaceCategory.PARK,
            [
                {"center": {"lat": "17.4401", "lon": "78.3501"}, "tags": {"name": "Far Park"}},
                {"lat": "17.44001", "lon": "78.35001", "tags": {"name": "Near Park"}},
                {"lat": "17.44002", "lon": "78.35002", "tags": {}},
            ],
            Decimal("17.440000"),
            Decimal("78.350000"),
        )
        self.assertEqual(result.nearest, NearbyPlace("Near Park", 2))
        self.assertEqual(result.park_count, 3)

    async def test_cache_hit_avoids_provider_call(self) -> None:
        cache = _CacheRepository()
        provider = _OverpassClient()
        service = NearbyPlaceService(cache, provider, _Settings())
        property_record = SimpleNamespace(latitude=Decimal("17.440000"), longitude=Decimal("78.350000"))

        first = await service.enrich_property(property_record)
        second = await service.enrich_property(property_record)

        self.assertEqual(first.provider_queries, 1)
        self.assertEqual(second.cache_hits, 4)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(second.metro.nearest.name, "metro place")
