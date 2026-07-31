"""Cache-first orchestration for enriching properties with locality coordinates."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Iterable

from sqlalchemy.exc import SQLAlchemyError

from app.models.geocode_cache import GeocodeCache
from app.repositories.geocode_cache import GeocodeCacheRepository
from app.repositories.property import PropertyRepository
from app.services.geocoding import GeocodingFailureReason, GeocodingResult, NominatimGeocodingClient
from app.utils.geospatial import Coordinate, normalize_locality

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class LocalityEnrichmentResult:
    """One cached or provider-derived locality enrichment outcome."""

    locality: str
    location_key: str
    status: str
    coordinate: Coordinate | None
    cache_hit: bool
    properties_updated: int


@dataclass(frozen=True)
class GeospatialEnrichmentSummary:
    """Aggregate result returned after a geospatial enrichment run."""

    total_localities: int
    cache_hits: int
    provider_queries: int
    successful_localities: int
    failed_localities: int
    properties_updated: int


@dataclass(frozen=True)
class RemainingFailedLocality:
    """One unresolved locality with a classified cached failure."""

    locality: str
    property_count: int
    failure_reason: str | None


@dataclass(frozen=True)
class GeocodingCoverageSummary:
    """Coverage metrics emitted after a geocoding run."""

    total_properties: int
    geocoded_properties: int
    remaining_properties: int
    top_remaining_failed_localities: list[RemainingFailedLocality]


async def get_geocoding_coverage_summary(
    property_repository: PropertyRepository,
    cache_repository: GeocodeCacheRepository,
    *,
    top_failed_limit: int = 10,
) -> GeocodingCoverageSummary:
    """Summarize coordinate coverage and the highest-impact classified failures."""
    total_properties, geocoded_properties = await property_repository.coordinate_coverage_counts()
    remaining_localities = await property_repository.list_remaining_coordinate_localities()
    cache_entries = await cache_repository.get_many(
        [normalize_locality(locality) for locality, _ in remaining_localities]
    )
    failed_localities = [
        RemainingFailedLocality(
            locality=locality,
            property_count=property_count,
            failure_reason=cache_entry.failure_reason,
        )
        for locality, property_count in remaining_localities
        if (cache_entry := cache_entries.get(normalize_locality(locality))) is not None
        and cache_entry.status == "failed"
    ]
    return GeocodingCoverageSummary(
        total_properties=total_properties,
        geocoded_properties=geocoded_properties,
        remaining_properties=total_properties - geocoded_properties,
        top_remaining_failed_localities=failed_localities[:top_failed_limit],
    )


class PropertyGeospatialService:
    """Resolve localities once and propagate validated coordinates to properties."""

    def __init__(
        self,
        property_repository: PropertyRepository,
        cache_repository: GeocodeCacheRepository,
        geocoding_client: NominatimGeocodingClient,
    ) -> None:
        self._property_repository = property_repository
        self._cache_repository = cache_repository
        self._geocoding_client = geocoding_client

    async def enrich_localities(
        self,
        localities: Iterable[str],
        *,
        retry_failed_cache: bool = False,
    ) -> tuple[list[LocalityEnrichmentResult], GeospatialEnrichmentSummary]:
        """Resolve each unique input locality and update every matching database property."""
        results: list[LocalityEnrichmentResult] = []
        seen_keys: set[str] = set()
        for locality in localities:
            location_key = normalize_locality(locality)
            if location_key in seen_keys:
                continue
            seen_keys.add(location_key)
            results.append(await self._enrich_locality(locality, location_key, retry_failed_cache))

        summary = GeospatialEnrichmentSummary(
            total_localities=len(results),
            cache_hits=sum(result.cache_hit for result in results),
            provider_queries=sum(not result.cache_hit for result in results),
            successful_localities=sum(result.status == "success" for result in results),
            failed_localities=sum(result.status != "success" for result in results),
            properties_updated=sum(result.properties_updated for result in results),
        )
        return results, summary

    async def _enrich_locality(
        self,
        locality: str,
        location_key: str,
        retry_failed_cache: bool,
    ) -> LocalityEnrichmentResult:
        """Use a durable cache entry or make one new provider request for a locality."""
        cached = await self._cache_repository.get(location_key)
        should_reclassify_legacy_failure = cached is not None and cached.status == "failed" and cached.failure_reason is None
        if cached is not None and not (retry_failed_cache or should_reclassify_legacy_failure):
            coordinate = self._coordinate_from_cache(cached)
            updated = await self._apply_coordinates(locality, coordinate)
            return LocalityEnrichmentResult(locality, location_key, cached.status, coordinate, True, updated)

        provider_result = await self._geocoding_client.geocode(locality)
        status = "success" if provider_result.coordinate else (
            "not_found" if provider_result.failure_reason is GeocodingFailureReason.EMPTY_RESPONSE else "failed"
        )
        cache_entry = cached or GeocodeCache(
            location_key=location_key,
            locality=locality,
            provider=self._geocoding_client.provider_name,
            status=status,
        )
        self._apply_provider_result(cache_entry, locality, status, provider_result)
        try:
            await self._cache_repository.save(cache_entry)
            updated = await self._apply_coordinates(locality, provider_result.coordinate)
        except SQLAlchemyError as error:
            diagnostics = provider_result.diagnostics
            LOGGER.exception(
                "geocode_cache_write_failed locality=%s http_status=%s raw_result_count=%s selected_latitude=%s selected_longitude=%s validation_result=%s failure_reason=%s error_message=%s",
                locality,
                diagnostics.http_status,
                diagnostics.raw_result_count,
                diagnostics.selected_latitude,
                diagnostics.selected_longitude,
                diagnostics.validation_result,
                GeocodingFailureReason.DATABASE_WRITE_FAILED.value,
                error,
            )
            raise
        return LocalityEnrichmentResult(locality, location_key, status, provider_result.coordinate, False, updated)

    def _apply_provider_result(
        self,
        cache_entry: GeocodeCache,
        locality: str,
        status: str,
        provider_result: GeocodingResult,
    ) -> None:
        """Refresh one cache record from a classified provider outcome without re-keying it."""
        cache_entry.locality = locality
        cache_entry.provider = self._geocoding_client.provider_name
        cache_entry.status = status
        cache_entry.latitude = provider_result.coordinate.latitude if provider_result.coordinate else None
        cache_entry.longitude = provider_result.coordinate.longitude if provider_result.coordinate else None
        cache_entry.display_name = provider_result.display_name
        cache_entry.error_message = provider_result.error_message
        cache_entry.failure_reason = provider_result.failure_reason.value if provider_result.failure_reason else None

    @staticmethod
    def _coordinate_from_cache(cache_entry: GeocodeCache) -> Coordinate | None:
        """Reconstruct a coordinate only for complete successful cache entries."""
        if cache_entry.status != "success" or cache_entry.latitude is None or cache_entry.longitude is None:
            return None
        return Coordinate(latitude=cache_entry.latitude, longitude=cache_entry.longitude)

    async def _apply_coordinates(self, locality: str, coordinate: Coordinate | None) -> int:
        """Update all matching properties only when a validated coordinate exists."""
        if coordinate is None:
            return 0
        return await self._property_repository.fill_missing_coordinates_for_location(
            locality, coordinate.latitude, coordinate.longitude
        )
