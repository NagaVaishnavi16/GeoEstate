"""Unit tests for search request range validation."""

import unittest

from pydantic import ValidationError

from app.schemas.property import PropertySearchRequest


class PropertySearchRequestTests(unittest.TestCase):
    """Verify invalid range combinations never enter the search service."""

    def test_rejects_inverted_price_range(self) -> None:
        with self.assertRaises(ValidationError):
            PropertySearchRequest(min_price=9000000, max_price=5000000)

    def test_accepts_requested_example_shape(self) -> None:
        request = PropertySearchRequest(
            location="Gachibowli",
            min_price=5000000,
            max_price=9000000,
            bedrooms=3,
            limit=20,
            offset=0,
            sort_by="price",
        )
        self.assertEqual(request.location, "Gachibowli")
        self.assertEqual(request.limit, 20)
