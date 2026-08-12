"""Offline unit tests for Gemini parsing and safe natural-search orchestration."""

import unittest

import httpx

from app.schemas.natural_search import ExtractedPropertyFilters, NearbyIntentFilters
from app.services.gemini_parser import GeminiParser, ParserFailure
from app.services.natural_language_search import NaturalLanguageSearchService
from app.services.search_types import PropertySortField


class _Settings:
    gemini_api_key = "test-key"
    gemini_model = "gemini-2.5-flash"
    gemini_timeout_seconds = 1


class _ParserWithPayload(GeminiParser):
    def __init__(self, payload: object) -> None:
        super().__init__(_Settings())
        self.payload = payload

    async def _request_structured_output(self, query: str) -> object:
        return self.payload


class _ParserWithException(GeminiParser):
    def __init__(self, error: Exception) -> None:
        super().__init__(_Settings())
        self.error = error

    async def _request_structured_output(self, query: str) -> object:
        raise self.error


class _StaticParser:
    def __init__(self, result: ExtractedPropertyFilters | ParserFailure) -> None:
        self.result = result

    async def parse(self, query: str):
        return self.result


class _SearchService:
    def __init__(self) -> None:
        self.criteria = None

    async def search(self, criteria):
        self.criteria = criteria
        return [], 0


class NaturalLanguageSearchTests(unittest.IsolatedAsyncioTestCase):
    """Ensure malformed AI output never executes the canonical search service."""

    async def test_gemini_payload_is_validated_as_structured_filters(self) -> None:
        parser = _ParserWithPayload(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": '{"property_type":"Apartment","bhk":3,"locality":"Gachibowli","price_min":null,"price_max":10000000,"area_min":null,"area_max":null,"building_status":null,"nearby":{"metro":true,"hospital":false,"school":false,"park":false},"sort_by":"price","sort_order":"asc","needs_clarification":false,"clarification_message":null,"missing_fields":[]}'
                                }
                            ]
                        }
                    }
                ]
            }
        )
        parsed = await parser.parse("3 BHK under one crore near metro")
        self.assertIsInstance(parsed, ExtractedPropertyFilters)
        self.assertEqual(parsed.price_max, 10_000_000)

    async def test_invalid_gemini_payload_returns_failure_without_search(self) -> None:
        parser = _ParserWithPayload({"candidates": []})
        result = await parser.parse("anything")
        self.assertIsInstance(result, ParserFailure)

        search = _SearchService()
        service = NaturalLanguageSearchService(_StaticParser(result), search)
        response = await service.search(query="anything", limit=20, offset=0)
        self.assertEqual(response.status, "validation_error")
        self.assertIsNone(search.criteria)

    async def test_extra_model_filter_is_rejected_without_search(self) -> None:
        parser = _ParserWithPayload(
            {"candidates": [{"content": {"parts": [{"text": '{"locality":"Gachibowli","unsafe_sql":"SELECT *"}'}]}}]}
        )
        result = await parser.parse("anything")
        self.assertIsInstance(result, ParserFailure)

    async def test_malformed_json_returns_failure_without_search(self) -> None:
        parser = _ParserWithPayload(
            {"candidates": [{"content": {"parts": [{"text": "{not valid JSON"}]}}]}
        )
        result = await parser.parse("anything")
        self.assertIsInstance(result, ParserFailure)

        search = _SearchService()
        response = await NaturalLanguageSearchService(_StaticParser(result), search).search(
            query="anything", limit=20, offset=0
        )
        self.assertEqual(response.status, "validation_error")
        self.assertIsNone(search.criteria)

    async def test_provider_timeout_returns_failure_without_search(self) -> None:
        result = await _ParserWithException(httpx.TimeoutException("timed out")).parse("anything")
        self.assertIsInstance(result, ParserFailure)

        search = _SearchService()
        response = await NaturalLanguageSearchService(_StaticParser(result), search).search(
            query="anything", limit=20, offset=0
        )
        self.assertEqual(response.status, "validation_error")
        self.assertIsNone(search.criteria)

    async def test_missing_api_key_returns_failure_without_provider_request(self) -> None:
        class _MissingKeySettings:
            gemini_api_key = None
            gemini_model = "gemini-2.5-flash"
            gemini_timeout_seconds = 1

        result = await GeminiParser(_MissingKeySettings()).parse("anything")
        self.assertIsInstance(result, ParserFailure)
        self.assertIn("GEMINI_API_KEY", result.message)

    async def test_validated_intent_reuses_existing_search_service(self) -> None:
        filters = ExtractedPropertyFilters(
            property_type="Apartment",
            bhk=3,
            locality="Gachibowli",
            price_max=10_000_000,
            nearby=NearbyIntentFilters(metro=True),
            sort_by=PropertySortField.PRICE,
        )
        search = _SearchService()
        response = await NaturalLanguageSearchService(_StaticParser(filters), search).search(
            query="3 BHK apartments under 1 crore near metro", limit=20, offset=0
        )
        self.assertEqual(response.status, "completed")
        self.assertEqual(search.criteria.location, "Gachibowli")
        self.assertTrue(search.criteria.near_metro)

    async def test_gachibowli_near_metro_query_preserves_metro_proximity_filter(self) -> None:
        filters = ExtractedPropertyFilters(
            property_type="Apartment",
            bhk=3,
            locality="Gachibowli",
            price_max=10_000_000,
            nearby=NearbyIntentFilters(metro=True),
        )
        search = _SearchService()
        response = await NaturalLanguageSearchService(_StaticParser(filters), search).search(
            query="Show me 3 BHK apartments under 1 crore in Gachibowli near metro",
            limit=20,
            offset=0,
        )
        self.assertEqual(response.status, "completed")
        self.assertEqual(search.criteria.location, "Gachibowli")
        self.assertEqual(search.criteria.max_price, 10_000_000)
        self.assertEqual(search.criteria.bedrooms, 3)
        self.assertEqual(search.criteria.property_type, "Apartment")
        self.assertTrue(search.criteria.near_metro)

    async def test_ambiguity_returns_clarification_without_search(self) -> None:
        filters = ExtractedPropertyFilters(
            needs_clarification=True,
            clarification_message="What is your maximum budget?",
            missing_fields=["price_max"],
        )
        search = _SearchService()
        response = await NaturalLanguageSearchService(_StaticParser(filters), search).search(
            query="show me properties", limit=20, offset=0
        )
        self.assertEqual(response.status, "needs_clarification")
        self.assertIsNone(search.criteria)

    async def test_empty_valid_intent_returns_clarification_without_search(self) -> None:
        search = _SearchService()
        response = await NaturalLanguageSearchService(_StaticParser(ExtractedPropertyFilters()), search).search(
            query="show me properties", limit=20, offset=0
        )
        self.assertEqual(response.status, "needs_clarification")
        self.assertIsNone(search.criteria)
