"""Reusable, rate-limited Nominatim client for locality-level geocoding."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum
import logging

import httpx

from app.core.config import Settings
from app.utils.geospatial import Coordinate, CoordinateValidationError, normalize_locality, validate_telangana_coordinate

LOGGER = logging.getLogger(__name__)
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


class GeocodingFailureReason(StrEnum):
    """Machine-readable causes for an unsuccessful geocoding attempt."""

    EMPTY_RESPONSE = "empty_response"
    COORDINATE_VALIDATION_FAILED = "coordinate_validation_failed"
    PARSER_FAILED = "parser_failed"
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    DATABASE_WRITE_FAILED = "database_write_failed"


@dataclass(frozen=True)
class GeocodingDiagnostics:
    """Provider diagnostics retained in logs for every geocoding outcome."""

    http_status: int | None
    raw_result_count: int | None
    selected_latitude: str | None
    selected_longitude: str | None
    validation_result: str
    query: str


@dataclass(frozen=True)
class GeocodingResult:
    """Normalized result returned by a geocoding provider."""

    coordinate: Coordinate | None
    display_name: str | None
    error_message: str | None
    failure_reason: GeocodingFailureReason | None
    diagnostics: GeocodingDiagnostics


class NominatimGeocodingClient:
    """Respectful async Nominatim client for Telangana locality lookups."""

    provider_name = "nominatim"

    def __init__(self, settings: Settings) -> None:
        if "configure-in-env" in settings.geocoding_user_agent:
            raise ValueError("GEOCODING_USER_AGENT must identify the application and a contact address")
        self._settings = settings
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.geocoding_timeout_seconds),
            headers={"User-Agent": settings.geocoding_user_agent, "Accept": "application/json"},
        )
        self._request_lock = asyncio.Lock()

    async def __aenter__(self) -> "NominatimGeocodingClient":
        """Support deterministic closing via an async context manager."""
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """Close the reusable HTTP client."""
        await self._client.aclose()

    async def geocode(self, locality: str) -> GeocodingResult:
        """Resolve one locality with alias-aware, progressively simpler queries."""
        last_result: GeocodingResult | None = None
        for query in self._build_query_candidates(locality):
            result = await self._query_nominatim(locality, query)
            if result.coordinate is not None:
                return result
            last_result = result
            if result.failure_reason not in {
                GeocodingFailureReason.EMPTY_RESPONSE,
                GeocodingFailureReason.COORDINATE_VALIDATION_FAILED,
            }:
                return result
            LOGGER.info(
                "geocode_query_fallback locality=%s failed_query=%s failure_reason=%s",
                locality,
                query,
                result.failure_reason.value if result.failure_reason else None,
            )
        if last_result is None:
            return self._failure(
                locality,
                GeocodingFailureReason.PARSER_FAILED,
                "No geocoding query candidates were generated",
                query=locality,
            )
        return last_result

    def _build_query_candidates(self, locality: str) -> tuple[str, ...]:
        """Prefer Hyderabad results, then progressively relax aliases and locality scope."""
        original = " ".join(locality.split())
        aliases = {
            normalize_locality(alias_key): alias_value
            for alias_key, alias_value in self._settings.geocoding_locality_aliases.items()
        }
        alias = aliases.get(normalize_locality(original), original)
        canonical = " ".join(alias.split())
        candidates = (
            f"{original}, Hyderabad, Telangana, India",
            f"{canonical}, Hyderabad, Telangana, India",
            canonical,
            f"{canonical}, Telangana, India",
            f"{canonical}, India",
        )
        return tuple(dict.fromkeys(candidate for candidate in candidates if candidate))

    async def _query_nominatim(self, locality: str, query: str) -> GeocodingResult:
        """Execute and classify one Nominatim query attempt."""
        response: httpx.Response | None = None
        async with self._request_lock:
            try:
                response = await self._client.get(
                    NOMINATIM_SEARCH_URL,
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "limit": 1,
                        "addressdetails": 1,
                        **({"email": self._settings.geocoding_email} if self._settings.geocoding_email else {}),
                    },
                )
                response.raise_for_status()
            except httpx.TimeoutException as error:
                return self._failure(
                    locality,
                    GeocodingFailureReason.TIMEOUT,
                    str(error),
                    query=query,
                    http_status=response.status_code if response is not None else None,
                )
            except httpx.HTTPStatusError as error:
                return self._failure(
                    locality,
                    GeocodingFailureReason.HTTP_ERROR,
                    str(error),
                    query=query,
                    http_status=error.response.status_code,
                )
            except httpx.HTTPError as error:
                return self._failure(locality, GeocodingFailureReason.HTTP_ERROR, str(error), query=query)
            finally:
                await asyncio.sleep(self._settings.geocoding_request_delay_seconds)

        if response is None:
            return self._failure(locality, GeocodingFailureReason.HTTP_ERROR, "No HTTP response was returned", query=query)
        try:
            payload = response.json()
        except ValueError as error:
            return self._failure(
                locality,
                GeocodingFailureReason.PARSER_FAILED,
                f"Response JSON parsing failed: {error}",
                query=query,
                http_status=response.status_code,
            )
        if not isinstance(payload, list):
            return self._failure(
                locality,
                GeocodingFailureReason.PARSER_FAILED,
                f"Expected a JSON list but received {type(payload).__name__}",
                query=query,
                http_status=response.status_code,
            )
        if not payload:
            return self._failure(
                locality,
                GeocodingFailureReason.EMPTY_RESPONSE,
                "Nominatim returned an empty result list",
                query=query,
                http_status=response.status_code,
                raw_result_count=0,
            )
        first_match = payload[0]
        if not isinstance(first_match, dict):
            return self._failure(
                locality,
                GeocodingFailureReason.PARSER_FAILED,
                "First Nominatim result is not an object",
                query=query,
                http_status=response.status_code,
                raw_result_count=len(payload),
            )
        selected_latitude = first_match.get("lat")
        selected_longitude = first_match.get("lon")
        display_name = first_match.get("display_name")
        if not isinstance(selected_latitude, str) or not isinstance(selected_longitude, str):
            return self._failure(
                locality,
                GeocodingFailureReason.PARSER_FAILED,
                "Selected Nominatim result does not contain string lat/lon values",
                query=query,
                http_status=response.status_code,
                raw_result_count=len(payload),
                selected_latitude=str(selected_latitude) if selected_latitude is not None else None,
                selected_longitude=str(selected_longitude) if selected_longitude is not None else None,
                display_name=display_name if isinstance(display_name, str) else None,
            )
        try:
            coordinate = validate_telangana_coordinate(selected_latitude, selected_longitude)
        except CoordinateValidationError as error:
            return self._failure(
                locality,
                GeocodingFailureReason.COORDINATE_VALIDATION_FAILED,
                str(error),
                query=query,
                http_status=response.status_code,
                raw_result_count=len(payload),
                selected_latitude=selected_latitude,
                selected_longitude=selected_longitude,
                display_name=display_name if isinstance(display_name, str) else None,
            )
        diagnostics = GeocodingDiagnostics(
            http_status=response.status_code,
            raw_result_count=len(payload),
            selected_latitude=selected_latitude,
            selected_longitude=selected_longitude,
            validation_result="passed",
            query=query,
        )
        LOGGER.info(
            "geocode_succeeded locality=%s query=%s http_status=%s raw_result_count=%s selected_latitude=%s selected_longitude=%s validation_result=%s",
            locality,
            diagnostics.query,
            diagnostics.http_status,
            diagnostics.raw_result_count,
            diagnostics.selected_latitude,
            diagnostics.selected_longitude,
            diagnostics.validation_result,
        )
        return GeocodingResult(
            coordinate=coordinate,
            display_name=display_name if isinstance(display_name, str) else None,
            error_message=None,
            failure_reason=None,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _failure(
        locality: str,
        failure_reason: GeocodingFailureReason,
        error_message: str,
        *,
        query: str,
        http_status: int | None = None,
        raw_result_count: int | None = None,
        selected_latitude: str | None = None,
        selected_longitude: str | None = None,
        display_name: str | None = None,
    ) -> GeocodingResult:
        """Build and log a fully classified failed attempt with provider diagnostics."""
        validation_result = "failed" if failure_reason is GeocodingFailureReason.COORDINATE_VALIDATION_FAILED else "not_attempted"
        diagnostics = GeocodingDiagnostics(
            http_status=http_status,
            raw_result_count=raw_result_count,
            selected_latitude=selected_latitude,
            selected_longitude=selected_longitude,
            validation_result=validation_result,
            query=query,
        )
        LOGGER.warning(
            "geocode_failed locality=%s query=%s http_status=%s raw_result_count=%s selected_latitude=%s selected_longitude=%s validation_result=%s failure_reason=%s error_message=%s",
            locality,
            diagnostics.query,
            diagnostics.http_status,
            diagnostics.raw_result_count,
            diagnostics.selected_latitude,
            diagnostics.selected_longitude,
            diagnostics.validation_result,
            failure_reason.value,
            error_message,
        )
        return GeocodingResult(
            coordinate=None,
            display_name=display_name,
            error_message=error_message,
            failure_reason=failure_reason,
            diagnostics=diagnostics,
        )
