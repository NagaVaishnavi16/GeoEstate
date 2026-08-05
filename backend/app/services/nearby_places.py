"""Cache-first, transport-independent nearby-place enrichment using Overpass."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from enum import StrEnum
import logging
from math import asin, cos, radians, sin, sqrt
from typing import Any

import httpx

from app.core.config import Settings
from app.models.nearby_place_cache import NearbyPlaceCache
from app.models.property import Property
from app.repositories.nearby_place_cache import NearbyPlaceCacheRepository

LOGGER = logging.getLogger(__name__)
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)


class PlaceCategory(StrEnum):
    """Nearby-place categories supplied by the Overpass provider."""

    METRO = "metro"
    HOSPITAL = "hospital"
    SCHOOL = "school"
    PARK = "park"


class OverpassProviderError(RuntimeError):
    """Raised when Overpass cannot provide a result after bounded retries."""


@dataclass(frozen=True)
class OverpassDeferred:
    """Temporary provider pause that must end the current ETL run without failure."""

    reason: str
    last_endpoint: str


@dataclass(frozen=True)
class NearbyPlace:
    """A named OSM feature with its computed distance from the property."""

    name: str
    distance_m: int


@dataclass(frozen=True)
class CategoryNearbyResult:
    """Nearest feature and optional park density for one category."""

    nearest: NearbyPlace | None
    park_count: int | None = None


@dataclass(frozen=True)
class NearbyPlaceEnrichment:
    """Complete nearby-place output for one property, without persistence concerns."""

    metro: CategoryNearbyResult
    hospital: CategoryNearbyResult
    school: CategoryNearbyResult
    park: CategoryNearbyResult
    cache_hits: int
    provider_queries: int
    deferred: bool = False


class OverpassClient:
    """Rate-limited async Overpass client with bounded exponential retry behavior."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # overpass-api.de rejects anonymous/default programmatic clients with HTTP 406.
        # Reuse the configured application identity already required for Nominatim.
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.overpass_timeout_seconds),
            headers={
                "User-Agent": settings.geocoding_user_agent,
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        self._request_lock = asyncio.Lock()
        self._endpoints = tuple(dict.fromkeys((settings.overpass_url, *OVERPASS_ENDPOINTS)))
        self._endpoint_index = 0
        self._endpoint_failures = {endpoint: 0 for endpoint in self._endpoints}
        self._consecutive_rate_limits = 0
        self._temporarily_rate_limited = False

    async def __aenter__(self) -> "OverpassClient":
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self._client.aclose()

    async def search_all(
        self,
        latitude: Decimal,
        longitude: Decimal,
    ) -> dict[PlaceCategory, list[dict[str, Any]]] | OverpassDeferred:
        """Fetch all four nearby-place categories in one combined Overpass request."""
        if self._temporarily_rate_limited:
            return OverpassDeferred("provider_circuit_open", self._current_endpoint)
        query = self.build_combined_query(latitude, longitude)
        last_error: Exception | None = None
        max_attempts = max(
            self._settings.overpass_max_retries,
            len(self._endpoints) * self._settings.overpass_max_endpoint_failures,
        )
        for attempt in range(max_attempts):
            endpoint = self._current_endpoint
            try:
                async with self._request_lock:
                    LOGGER.info(
                        "overpass_query categories=metro,hospital,school,park method=POST endpoint=%s attempt=%d content_type=application/x-www-form-urlencoded query=%s",
                        self._current_endpoint,
                        attempt + 1,
                        query,
                    )
                    response = await self._client.post(endpoint, data={"data": query})
                    if response.status_code in {408, 429} or 500 <= response.status_code <= 599:
                        last_error = OverpassProviderError(f"{response.status_code} from {endpoint}")
                        await self._handle_temporary_failure(
                            endpoint,
                            attempt,
                            status_code=response.status_code,
                            retry_after=response.headers.get("Retry-After"),
                        )
                        if self._temporarily_rate_limited:
                            return OverpassDeferred("temporary_http_failure", endpoint)
                        continue
                    response.raise_for_status()
                    payload = response.json()
                    await asyncio.sleep(self._settings.overpass_success_delay_seconds)
                if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
                    raise OverpassProviderError("Overpass response did not contain an elements list")
                self._endpoint_failures[endpoint] = 0
                self._consecutive_rate_limits = 0
                return self._split_categories(payload["elements"])
            except httpx.TimeoutException as error:
                last_error = error
                await self._handle_temporary_failure(endpoint, attempt, reason="timeout")
                if self._temporarily_rate_limited:
                    return OverpassDeferred("timeout", endpoint)
            except httpx.RequestError as error:
                last_error = error
                await self._handle_temporary_failure(endpoint, attempt, reason="request_error")
                if self._temporarily_rate_limited:
                    return OverpassDeferred("request_error", endpoint)
            except (httpx.HTTPError, ValueError, OverpassProviderError) as error:
                last_error = error
                if attempt + 1 == max_attempts:
                    break
                delay = self._settings.overpass_retry_backoff_seconds * (2**attempt)
                LOGGER.warning(
                    "overpass_retry endpoint=%s attempt=%d delay_seconds=%s error=%s",
                    self._current_endpoint,
                    attempt + 1,
                    delay,
                    error,
                )
                await asyncio.sleep(delay)
        if self._temporarily_rate_limited:
            return OverpassDeferred("temporary_provider_failure", self._current_endpoint)
        raise OverpassProviderError(f"Combined Overpass lookup failed: {last_error}")

    @property
    def _current_endpoint(self) -> str:
        """Return the active endpoint in the configured fallback sequence."""
        return self._endpoints[self._endpoint_index]

    async def _handle_temporary_failure(
        self,
        endpoint: str,
        attempt: int,
        *,
        status_code: int | None = None,
        retry_after: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Back off and fail over after temporary rate, timeout, or server failures."""
        self._endpoint_failures[endpoint] += 1
        if status_code == 429:
            self._consecutive_rate_limits += 1
        retry_delay = self._retry_delay(status_code, retry_after, attempt)
        LOGGER.warning(
            "overpass_endpoint_failure endpoint=%s status_code=%s reason=%s failure_count=%d retry_delay_seconds=%s",
            endpoint,
            status_code,
            reason,
            self._endpoint_failures[endpoint],
            retry_delay,
        )
        await asyncio.sleep(retry_delay)
        if self._endpoint_failures[endpoint] >= self._settings.overpass_max_endpoint_failures and self._endpoint_index < len(self._endpoints) - 1:
            self._endpoint_index += 1
            LOGGER.warning(
                "overpass_endpoint_failover previous_endpoint=%s next_endpoint=%s status_code=%s",
                endpoint,
                self._current_endpoint,
                status_code,
            )
        elif self._endpoint_failures[endpoint] >= self._settings.overpass_max_endpoint_failures:
            self._temporarily_rate_limited = True
            LOGGER.warning(
                "overpass_temporarily_unavailable reason=all_endpoints_exhausted last_endpoint=%s status_code=%s",
                endpoint,
                status_code,
            )
        if self._consecutive_rate_limits >= self._settings.overpass_max_consecutive_rate_limits:
            self._temporarily_rate_limited = True
            LOGGER.warning(
                "overpass_temporarily_unavailable reason=max_consecutive_rate_limits consecutive_rate_limits=%d",
                self._consecutive_rate_limits,
            )

    def _retry_delay(self, status_code: int | None, retry_after: str | None, attempt: int) -> float:
        """Use Retry-After for 429 when valid, otherwise use configured exponential backoff."""
        if status_code == 429:
            parsed_delay = self._parse_retry_after(retry_after)
            if parsed_delay is not None:
                return parsed_delay
        return self._settings.overpass_retry_backoff_seconds * (2**attempt)

    @staticmethod
    def _parse_retry_after(value: str | None) -> float | None:
        """Parse Retry-After delta seconds or an HTTP date into a non-negative delay."""
        if value is None:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
            except (TypeError, ValueError, IndexError):
                return None
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())

    def build_combined_query(self, latitude: Decimal, longitude: Decimal) -> str:
        """Return one Overpass QL union query for metro, hospital, school, and park."""
        radius = self._settings.overpass_search_radius_m
        latitude_text = format(latitude, "f")
        longitude_text = format(longitude, "f")
        return (
            "[out:json][timeout:25];("
            f'nwr(around:{radius},{latitude_text},{longitude_text})["railway"="station"]["station"="subway"];'
            f'nwr(around:{radius},{latitude_text},{longitude_text})["public_transport"="station"]["subway"="yes"];'
            f'nwr(around:{radius},{latitude_text},{longitude_text})["amenity"="hospital"];'
            f'nwr(around:{radius},{latitude_text},{longitude_text})["amenity"="school"];'
            f'nwr(around:{radius},{latitude_text},{longitude_text})["leisure"="park"];'
            ");out center tags;"
        )

    @staticmethod
    def _split_categories(elements: list[Any]) -> dict[PlaceCategory, list[dict[str, Any]]]:
        """Classify a combined Overpass response locally by verified OSM tags."""
        grouped: dict[PlaceCategory, list[dict[str, Any]]] = {category: [] for category in PlaceCategory}
        for element in elements:
            if not isinstance(element, dict):
                continue
            tags = element.get("tags")
            if not isinstance(tags, dict):
                continue
            if (tags.get("railway") == "station" and tags.get("station") == "subway") or (
                tags.get("public_transport") == "station" and tags.get("subway") == "yes"
            ):
                grouped[PlaceCategory.METRO].append(element)
            if tags.get("amenity") == "hospital":
                grouped[PlaceCategory.HOSPITAL].append(element)
            if tags.get("amenity") == "school":
                grouped[PlaceCategory.SCHOOL].append(element)
            if tags.get("leisure") == "park":
                grouped[PlaceCategory.PARK].append(element)
        return grouped


class NearbyPlaceService:
    """Resolve nearby verified OSM features using durable cache entries before Overpass."""

    def __init__(
        self,
        cache_repository: NearbyPlaceCacheRepository,
        overpass_client: OverpassClient,
        settings: Settings,
    ) -> None:
        self._cache_repository = cache_repository
        self._overpass_client = overpass_client
        self._settings = settings
        self._processed_buckets: set[str] = set()
        self._cached_buckets: set[str] = set()
        self._last_successful_coordinate_bucket: str | None = None

    async def enrich_property(self, property_record: Property) -> NearbyPlaceEnrichment:
        """Resolve four category outputs for a coordinate-complete property record."""
        if property_record.latitude is None or property_record.longitude is None:
            raise ValueError("Nearby-place enrichment requires latitude and longitude")
        bucket = self.coordinate_bucket(property_record.latitude, property_record.longitude)
        cached_entries: dict[PlaceCategory, NearbyPlaceCache | None] = {}
        results: dict[PlaceCategory, CategoryNearbyResult] = {}
        cache_hits = 0
        for category in PlaceCategory:
            cache_entry = await self._cache_repository.get(bucket, category.value)
            cached_entries[category] = cache_entry
            if cache_entry is not None and cache_entry.status in {"success", "not_found"}:
                results[category] = self._deserialize(cache_entry.result)
                cache_hits += 1

        provider_queries = 0
        if len(results) != len(PlaceCategory):
            combined_results = await self._overpass_client.search_all(
                property_record.latitude,
                property_record.longitude,
            )
            if isinstance(combined_results, OverpassDeferred):
                LOGGER.warning(
                    "nearby_bucket_deferred coordinate_bucket=%s reason=%s last_endpoint=%s",
                    bucket,
                    combined_results.reason,
                    combined_results.last_endpoint,
                )
                return self._deferred_enrichment(cache_hits)
            provider_queries = 1
            for category in PlaceCategory:
                if category in results:
                    continue
                result = self.select_nearest(
                    category,
                    combined_results[category],
                    property_record.latitude,
                    property_record.longitude,
                )
                cache_entry = cached_entries[category] or NearbyPlaceCache(
                    coordinate_bucket=bucket,
                    category=category.value,
                    status="not_found",
                )
                cache_entry.status = "success" if result.nearest is not None else "not_found"
                cache_entry.result = self._serialize(result)
                cache_entry.error_message = None
                await self._cache_repository.save(cache_entry)
                results[category] = result
            self._processed_buckets.add(bucket)
            self._last_successful_coordinate_bucket = bucket
        else:
            self._processed_buckets.add(bucket)
            self._cached_buckets.add(bucket)
            self._last_successful_coordinate_bucket = bucket
        return NearbyPlaceEnrichment(
            metro=results[PlaceCategory.METRO],
            hospital=results[PlaceCategory.HOSPITAL],
            school=results[PlaceCategory.SCHOOL],
            park=results[PlaceCategory.PARK],
            cache_hits=cache_hits,
            provider_queries=provider_queries,
        )

    def log_resume_summary(self) -> None:
        """Log Stage 3 progress when Overpass throttling pauses provider work."""
        processed_buckets = len(self._processed_buckets)
        cached_buckets = len(self._cached_buckets)
        # The cache is durable; any bucket not completed in this run remains selectable next run.
        total_buckets = self._settings.overpass_total_coordinate_buckets
        remaining_buckets = max(0, total_buckets - processed_buckets)
        completion_percentage = (processed_buckets / total_buckets * 100) if total_buckets else 100.0
        LOGGER.info(
            "nearby_resume_summary processed_buckets=%d cached_buckets=%d remaining_buckets=%d completion_percentage=%.2f last_successful_coordinate_bucket=%s",
            processed_buckets,
            cached_buckets,
            remaining_buckets,
            completion_percentage,
            self._last_successful_coordinate_bucket,
        )

    @staticmethod
    def _deferred_enrichment(cache_hits: int) -> NearbyPlaceEnrichment:
        """Return a non-persistent result that lets the pipeline commit and stop cleanly."""
        empty = CategoryNearbyResult(nearest=None)
        return NearbyPlaceEnrichment(
            metro=empty,
            hospital=empty,
            school=empty,
            park=empty,
            cache_hits=cache_hits,
            provider_queries=0,
            deferred=True,
        )

    @staticmethod
    def coordinate_bucket(latitude: Decimal, longitude: Decimal) -> str:
        """Create a stable ~100m cache bucket from six-decimal WGS84 coordinates."""
        return f"{latitude.quantize(Decimal('0.001'))}:{longitude.quantize(Decimal('0.001'))}"

    def select_nearest(
        self,
        category: PlaceCategory,
        elements: list[dict[str, Any]],
        latitude: Decimal,
        longitude: Decimal,
    ) -> CategoryNearbyResult:
        """Parse Overpass data, calculate distances, and select the nearest named feature."""
        places: list[NearbyPlace] = []
        park_count = 0
        for element in elements:
            distance_m = self._element_distance(element, latitude, longitude)
            if distance_m is not None and category is PlaceCategory.PARK and distance_m <= self._settings.overpass_park_count_radius_m:
                park_count += 1
            parsed = self._parse_element(element, latitude, longitude)
            if parsed is None:
                continue
            places.append(parsed)
        nearest = min(places, key=lambda place: (place.distance_m, place.name.casefold()), default=None)
        return CategoryNearbyResult(nearest=nearest, park_count=park_count if category is PlaceCategory.PARK else None)

    @staticmethod
    def _parse_element(element: dict[str, Any], latitude: Decimal, longitude: Decimal) -> NearbyPlace | None:
        """Parse an OSM node/way/relation with a usable name and center coordinate."""
        tags = element.get("tags")
        if not isinstance(tags, dict):
            return None
        name = tags.get("name")
        if not isinstance(name, str) or not name.strip():
            return None
        distance_m = NearbyPlaceService._element_distance(element, latitude, longitude)
        if distance_m is None:
            return None
        return NearbyPlace(
            name=" ".join(name.split())[:255],
            distance_m=distance_m,
        )

    @staticmethod
    def _element_distance(element: dict[str, Any], latitude: Decimal, longitude: Decimal) -> int | None:
        """Return the distance for an OSM node or a way/relation center when usable."""
        raw_latitude = element.get("lat")
        raw_longitude = element.get("lon")
        center = element.get("center")
        if isinstance(center, dict):
            raw_latitude = center.get("lat", raw_latitude)
            raw_longitude = center.get("lon", raw_longitude)
        try:
            place_latitude = Decimal(str(raw_latitude))
            place_longitude = Decimal(str(raw_longitude))
        except Exception:
            return None
        return haversine_distance_m(latitude, longitude, place_latitude, place_longitude)

    @staticmethod
    def _serialize(result: CategoryNearbyResult) -> dict[str, object]:
        return {
            "nearest": None if result.nearest is None else {"name": result.nearest.name, "distance_m": result.nearest.distance_m},
            "park_count": result.park_count,
        }

    @staticmethod
    def _deserialize(payload: dict[str, Any] | None) -> CategoryNearbyResult:
        """Rebuild a validated service result from the durable JSON cache payload."""
        if not isinstance(payload, dict):
            return CategoryNearbyResult(nearest=None)
        nearest_payload = payload.get("nearest")
        nearest: NearbyPlace | None = None
        if isinstance(nearest_payload, dict):
            name, distance_m = nearest_payload.get("name"), nearest_payload.get("distance_m")
            if isinstance(name, str) and isinstance(distance_m, int) and distance_m >= 0:
                nearest = NearbyPlace(name=name, distance_m=distance_m)
        park_count = payload.get("park_count")
        return CategoryNearbyResult(nearest=nearest, park_count=park_count if isinstance(park_count, int) and park_count >= 0 else None)


def haversine_distance_m(
    latitude_a: Decimal,
    longitude_a: Decimal,
    latitude_b: Decimal,
    longitude_b: Decimal,
) -> int:
    """Calculate a rounded great-circle distance in meters using WGS84 coordinates."""
    earth_radius_m = 6_371_000
    latitude_delta = radians(float(latitude_b - latitude_a))
    longitude_delta = radians(float(longitude_b - longitude_a))
    latitude_a_radians = radians(float(latitude_a))
    latitude_b_radians = radians(float(latitude_b))
    haversine = sin(latitude_delta / 2) ** 2 + cos(latitude_a_radians) * cos(latitude_b_radians) * sin(longitude_delta / 2) ** 2
    return round(2 * earth_radius_m * asin(sqrt(haversine)))
