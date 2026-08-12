"""Offline unit tests for deterministic property intelligence scoring."""

import unittest
from decimal import Decimal

from app.services.property_scoring import PropertyScoringInput, PropertyScoringService


def _input(**overrides: object) -> PropertyScoringInput:
    values: dict[str, object] = {
        "rate_per_sqft": Decimal("6000"),
        "area_sqft": 1500,
        "building_status": "Ready to move",
        "locality_average_price_per_sqft": Decimal("6000"),
        "locality_average_area_sqft": Decimal("1500"),
        "nearest_metro_distance_m": 100,
        "nearest_hospital_distance_m": 100,
        "nearest_school_distance_m": 100,
        "nearest_park_distance_m": 100,
        "nearby_park_count": 5,
        "nearest_metro": "Metro",
        "nearest_hospital": "Hospital",
        "nearest_school": "School",
        "nearest_park": "Park",
    }
    values.update(overrides)
    return PropertyScoringInput(**values)


class PropertyScoringServiceTests(unittest.TestCase):
    """Verify formulas are bounded, reproducible, and honest about missing evidence."""

    def setUp(self) -> None:
        self.service = PropertyScoringService()

    def test_excellent_connectivity_exceeds_poor_connectivity(self) -> None:
        excellent = self.service.connectivity_score(_input())
        poor = self.service.connectivity_score(
            _input(
                nearest_metro_distance_m=9_999,
                nearest_hospital_distance_m=9_999,
                nearest_school_distance_m=9_999,
            )
        )
        self.assertIsNotNone(excellent)
        self.assertIsNotNone(poor)
        self.assertGreater(excellent, poor)

    def test_connectivity_redistributes_missing_factor_weight(self) -> None:
        only_metro = self.service.connectivity_score(
            _input(nearest_hospital_distance_m=None, nearest_school_distance_m=None)
        )
        expected_metro = Decimal("100") * (-(Decimal("100") / Decimal("1500"))).exp()
        self.assertEqual(only_metro, expected_metro.quantize(Decimal("0.01")))
        self.assertIsNone(
            self.service.connectivity_score(
                _input(
                    nearest_metro_distance_m=None,
                    nearest_hospital_distance_m=None,
                    nearest_school_distance_m=None,
                )
            )
        )

    def test_excellent_green_coverage_exceeds_poor_coverage(self) -> None:
        excellent = self.service.green_score(_input())
        poor = self.service.green_score(_input(nearest_park_distance_m=9_999, nearby_park_count=0))
        self.assertIsNotNone(excellent)
        self.assertIsNotNone(poor)
        self.assertGreater(excellent, poor)

    def test_park_count_is_capped_at_five(self) -> None:
        at_cap = self.service.green_score(_input(nearest_park_distance_m=None, nearby_park_count=5))
        above_cap = self.service.green_score(_input(nearest_park_distance_m=None, nearby_park_count=12))
        self.assertEqual(at_cap, Decimal("100.00"))
        self.assertEqual(above_cap, Decimal("100.00"))

    def test_missing_locality_rate_benchmark_returns_null_investment(self) -> None:
        self.assertIsNone(self.service.investment_score(_input(locality_average_price_per_sqft=None)))

    def test_investment_score_boundary_cases_and_clamping(self) -> None:
        equal_rate = self.service.investment_score(_input())
        lower_rate = self.service.investment_score(_input(rate_per_sqft=Decimal("3000")))
        higher_rate = self.service.investment_score(_input(rate_per_sqft=Decimal("12000")))
        self.assertEqual(equal_rate, Decimal("100.00"))
        self.assertEqual(lower_rate, Decimal("100.00"))
        self.assertEqual(higher_rate, Decimal("75.00"))

    def test_repeated_calculation_is_deterministic_and_bounded(self) -> None:
        property_data = _input(nearest_metro_distance_m=20_000)
        first = self.service.score(property_data)
        second = self.service.score(property_data)
        self.assertEqual(first, second)
        for score in (first.connectivity_score, first.green_score, first.investment_score, first.liveability_score):
            if score is not None:
                self.assertGreaterEqual(score, Decimal("0"))
                self.assertLessEqual(score, Decimal("100"))

    def test_liveability_uses_declared_weights_without_investment(self) -> None:
        score = self.service.liveability_score(
            _input(
                nearest_hospital=None,
                nearest_school=None,
                nearest_park=None,
            ),
            connectivity=Decimal("100"),
            green=Decimal("50"),
        )
        # One verified amenity remains: 25 availability points.
        self.assertEqual(score, Decimal("62.50"))
