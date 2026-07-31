"""Unit tests for cache-first, non-destructive Stage 1 geocoding behavior."""

import unittest
from decimal import Decimal

from app.services.geocoding import GeocodingDiagnostics, GeocodingFailureReason, GeocodingResult
from app.services.geospatial_enrichment import PropertyGeospatialService
from app.utils.geospatial import Coordinate


class _FakeCacheRepository:
    def __init__(self) -> None:
        self.entries: dict[str, object] = {}
        self.added: list[object] = []

    async def get(self, location_key: str) -> object | None:
        return self.entries.get(location_key)

    async def save(self, cache_entry: object) -> object:
        self.added.append(cache_entry)
        self.entries[cache_entry.location_key] = cache_entry
        return cache_entry


class _FakePropertyRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Decimal, Decimal]] = []

    async def fill_missing_coordinates_for_location(
        self,
        locality: str,
        latitude: Decimal,
        longitude: Decimal,
    ) -> int:
        self.calls.append((locality, latitude, longitude))
        return 2


class _FakeGeocodingClient:
    provider_name = "test-provider"

    def __init__(self) -> None:
        self.queries: list[str] = []

    async def geocode(self, locality: str) -> GeocodingResult:
        self.queries.append(locality)
        return GeocodingResult(
            coordinate=Coordinate(Decimal("17.444000"), Decimal("78.350000")),
            display_name="Gachibowli, Hyderabad",
            error_message=None,
            failure_reason=None,
            diagnostics=GeocodingDiagnostics(
                http_status=200,
                raw_result_count=1,
                selected_latitude="17.444000",
                selected_longitude="78.350000",
                validation_result="passed",
                query="Gachibowli, Hyderabad, Telangana, India",
            ),
        )


class PropertyGeospatialServiceTests(unittest.IsolatedAsyncioTestCase):
    """Verify localities are queried once and updates delegate guarded persistence."""

    async def test_duplicate_locality_is_geocoded_once_and_cached(self) -> None:
        cache_repository = _FakeCacheRepository()
        property_repository = _FakePropertyRepository()
        geocoding_client = _FakeGeocodingClient()
        service = PropertyGeospatialService(property_repository, cache_repository, geocoding_client)

        _, summary = await service.enrich_localities(["Gachibowli", "  gachibowli  "])

        self.assertEqual(geocoding_client.queries, ["Gachibowli"])
        self.assertEqual(summary.total_localities, 1)
        self.assertEqual(summary.provider_queries, 1)
        self.assertEqual(summary.properties_updated, 2)
        self.assertEqual(len(cache_repository.added), 1)
        self.assertEqual(len(property_repository.calls), 1)

    async def test_validation_failure_is_persisted_with_machine_readable_reason(self) -> None:
        class FailingClient(_FakeGeocodingClient):
            async def geocode(self, locality: str) -> GeocodingResult:
                self.queries.append(locality)
                return GeocodingResult(
                    coordinate=None,
                    display_name="Incorrect result",
                    error_message="Latitude falls outside the Telangana validation range",
                    failure_reason=GeocodingFailureReason.COORDINATE_VALIDATION_FAILED,
                    diagnostics=GeocodingDiagnostics(
                        http_status=200,
                        raw_result_count=1,
                        selected_latitude="28.613900",
                        selected_longitude="77.209000",
                        validation_result="failed",
                        query="Kukatpally, Hyderabad, Telangana, India",
                    ),
                )

        cache_repository = _FakeCacheRepository()
        service = PropertyGeospatialService(
            _FakePropertyRepository(),
            cache_repository,
            FailingClient(),
        )

        _, summary = await service.enrich_localities(["Kukatpally"])

        cached_entry = cache_repository.added[0]
        self.assertEqual(summary.failed_localities, 1)
        self.assertEqual(cached_entry.status, "failed")
        self.assertEqual(cached_entry.failure_reason, "coordinate_validation_failed")
