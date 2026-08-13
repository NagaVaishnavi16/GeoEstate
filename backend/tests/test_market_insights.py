"""Offline tests for descriptive market-insights composition."""

import unittest
from decimal import Decimal
from types import SimpleNamespace

from app.services.market_insights import MarketInsightsService


class _Repository:
    async def price_distribution(self):
        return (20, Decimal("3000"), Decimal("4500"), Decimal("6000"), Decimal("8000"), Decimal("12000"))

    async def locality_price_metrics(self, *, limit: int):
        return [
            SimpleNamespace(
                locality="Gachibowli", total_listings=8, average_price_lakh=Decimal("90"),
                median_price_lakh=Decimal("85"), average_price_per_sqft=Decimal("8000"),
            )
        ]

    async def score_price_metrics(self):
        return [
            ("Investment", 4, Decimal("80"), Decimal("82"), Decimal("7000")),
            ("Connectivity", 4, Decimal("70"), Decimal("84"), Decimal("7100")),
            ("Green", 0, None, None, None),
            ("Liveability", 0, None, None, None),
        ]

    async def rate_outliers(self, *, limit: int):
        return [
            (
                SimpleNamespace(property_id="hyd-1", location="Gachibowli", price_lakh=Decimal("80"), rate_per_sqft=Decimal("9000")),
                Decimal("8000"), Decimal("1.125"),
            )
        ]

    async def amenity_price_metrics(self):
        return [
            ("Metro", 4, Decimal("84"), Decimal("7100"), Decimal("650")),
            ("Hospital", 0, None, None, None),
            ("School", 0, None, None, None),
            ("Park", 0, None, None, None),
        ]


class MarketInsightsServiceTests(unittest.IsolatedAsyncioTestCase):
    """Ensure statements are bounded and derived only from supplied aggregate facts."""

    async def test_composes_descriptive_insights_without_causal_language(self) -> None:
        response = await MarketInsightsService(_Repository()).get_insights()
        self.assertEqual(response.price_per_sqft_distribution.median, Decimal("6000"))
        self.assertEqual(response.locality_price_metrics[0].locality, "Gachibowli")
        self.assertEqual(response.rate_outliers[0].rate_to_locality_average, Decimal("1.125"))
        self.assertLessEqual(len(response.statements), 4)
        self.assertTrue(any("Gachibowli" in statement.text for statement in response.statements))
        self.assertFalse(any("return" in statement.text.casefold() for statement in response.statements))
