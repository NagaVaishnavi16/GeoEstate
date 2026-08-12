"""Regression tests proving score fields flow through existing search contracts unchanged."""

import unittest
from decimal import Decimal
from types import SimpleNamespace

from app.api.v1.search import search_properties
from app.schemas.property import PropertySearchRequest
from app.services.search import PropertySearchService


def _property() -> SimpleNamespace:
    return SimpleNamespace(
        property_id="hyd-score-1",
        title="3 BHK Apartment",
        location="Gachibowli",
        price_lakh=Decimal("80.00"),
        rate_per_sqft=Decimal("8000.00"),
        area_sqft=1000,
        building_status="Ready to move",
        bedrooms=3,
        latitude=Decimal("17.440000"),
        longitude=Decimal("78.350000"),
        investment_score=Decimal("88.50"),
        connectivity_score=Decimal("91.00"),
        green_score=Decimal("72.00"),
        liveability_score=Decimal("84.00"),
        nearest_metro="Raidurg Metro",
        nearest_hospital="Test Hospital",
        nearest_school="Test School",
        nearest_park="Test Park",
        nearest_metro_distance_m=200,
        nearest_hospital_distance_m=400,
        nearest_school_distance_m=350,
        nearest_park_distance_m=500,
        nearby_park_count=2,
        ai_summary=None,
    )


class _Repository:
    async def search(self, criteria):
        self.criteria = criteria
        return [_property()], 1


class SearchScoreRegressionTests(unittest.IsolatedAsyncioTestCase):
    """Scores are response fields only and must not alter existing search selection."""

    async def test_structured_search_returns_identical_result_with_populated_scores(self) -> None:
        repository = _Repository()
        response = await search_properties(
            PropertySearchRequest(location="Gachibowli", limit=20, offset=0),
            PropertySearchService(repository),
        )
        self.assertEqual(response.total, 1)
        self.assertEqual(response.items[0].property_id, "hyd-score-1")
        self.assertEqual(response.items[0].connectivity_score, Decimal("91.00"))
        self.assertEqual(response.items[0].investment_score, Decimal("88.50"))
