"""Unit tests for transport-neutral search criteria defaults."""

import unittest
from decimal import Decimal

from app.services.search_types import PropertySearchCriteria, PropertySortField, SortOrder


class SearchCriteriaTests(unittest.TestCase):
    """Verify the reusable search contract remains deterministic for non-HTTP callers."""

    def test_defaults_are_safe_and_deterministic(self) -> None:
        criteria = PropertySearchCriteria()
        self.assertEqual(criteria.limit, 20)
        self.assertEqual(criteria.offset, 0)
        self.assertEqual(criteria.sort_by, PropertySortField.PRICE)
        self.assertEqual(criteria.sort_order, SortOrder.ASC)

    def test_supports_ai_or_frontend_equivalent_filter_values(self) -> None:
        criteria = PropertySearchCriteria(
            location="Gachibowli",
            min_price=Decimal("5000000"),
            max_price=Decimal("9000000"),
            bedrooms=3,
        )
        self.assertEqual(criteria.location, "Gachibowli")
        self.assertEqual(criteria.max_price, Decimal("9000000"))
