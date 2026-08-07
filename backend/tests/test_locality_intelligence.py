"""Unit tests for locality intelligence response and service behavior."""

import unittest
from decimal import Decimal
from types import SimpleNamespace

from app.api.v1.localities import to_response
from app.services.locality_intelligence import LocalityIntelligenceService


def _record() -> SimpleNamespace:
    return SimpleNamespace(
        locality="Gachibowli",
        total_listings=12,
        average_price_lakh=Decimal("95.20"),
        median_price_lakh=Decimal("88.00"),
        minimum_price_lakh=Decimal("52.00"),
        maximum_price_lakh=Decimal("150.00"),
        average_built_up_area_sqft=Decimal("1450.00"),
        average_price_per_sqft=Decimal("6565.00"),
        centroid_latitude=Decimal("17.440000"),
        centroid_longitude=Decimal("78.348000"),
        metro_available_listings=10,
        hospital_available_listings=12,
        school_available_listings=11,
        park_available_listings=8,
        average_metro_distance_m=Decimal("350.00"),
        average_hospital_distance_m=Decimal("800.00"),
        average_school_distance_m=Decimal("500.00"),
        average_park_distance_m=Decimal("650.00"),
        average_nearby_park_count=Decimal("2.50"),
        average_investment_score=None,
        average_connectivity_score=None,
        average_green_score=None,
        average_liveability_score=None,
    )


class _Repository:
    async def list(self, *, limit: int, offset: int):
        return [_record()], 1

    async def get_by_locality(self, locality: str):
        return _record() if locality.casefold() == "gachibowli" else None

    async def list_by_average_price(self, *, descending: bool, limit: int):
        return [_record()]


class LocalityIntelligenceTests(unittest.IsolatedAsyncioTestCase):
    """Verify API response nesting and transport-independent service delegation."""

    def test_response_includes_current_enrichment_availability(self) -> None:
        response = to_response(_record())
        self.assertEqual(response.locality, "Gachibowli")
        self.assertEqual(response.enrichment.metro_available_listings, 10)
        self.assertEqual(response.centroid_longitude, Decimal("78.348000"))

    async def test_service_delegates_expensive_and_affordable_queries(self) -> None:
        service = LocalityIntelligenceService(_Repository())
        self.assertEqual(len(await service.top_expensive(limit=10)), 1)
        self.assertEqual(len(await service.most_affordable(limit=10)), 1)
        self.assertIsNotNone(await service.get_locality("Gachibowli"))
