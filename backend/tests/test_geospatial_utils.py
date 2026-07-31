"""Unit tests for provider-independent geospatial validation helpers."""

import unittest
from decimal import Decimal

from app.utils.geospatial import (
    CoordinateValidationError,
    normalize_locality,
    validate_hyderabad_coordinate,
    validate_telangana_coordinate,
)


class GeospatialUtilityTests(unittest.TestCase):
    """Verify cache-key normalization and Hyderabad coordinate guardrails."""

    def test_normalize_locality_collapses_case_and_whitespace(self) -> None:
        self.assertEqual(normalize_locality("  Banjara   Hills "), "banjara hills")

    def test_validate_hyderabad_coordinate_rounds_to_six_places(self) -> None:
        coordinate = validate_hyderabad_coordinate("17.4123456", "78.4345678")
        self.assertEqual(coordinate.latitude, Decimal("17.412346"))
        self.assertEqual(coordinate.longitude, Decimal("78.434568"))

    def test_validate_hyderabad_coordinate_rejects_out_of_region_result(self) -> None:
        with self.assertRaises(CoordinateValidationError):
            validate_hyderabad_coordinate("28.6139", "77.2090")

    def test_validate_telangana_coordinate_accepts_non_hyderabad_telangana_point(self) -> None:
        coordinate = validate_telangana_coordinate("17.729000", "79.595000")
        self.assertEqual(coordinate.latitude, Decimal("17.729000"))
        self.assertEqual(coordinate.longitude, Decimal("79.595000"))
