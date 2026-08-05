"""Run the production GeoEstate coordinate and geometry enrichment pipeline."""

from __future__ import annotations

import argparse
import asyncio
from contextlib import AsyncExitStack
import logging
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import AsyncSessionFactory
from app.repositories.geocode_cache import GeocodeCacheRepository
from app.repositories.property import PropertyRepository
from app.repositories.nearby_place_cache import NearbyPlaceCacheRepository
from app.services.geocoding import NominatimGeocodingClient
from app.services.enrichment_pipeline import EnrichmentStage, PropertyEnrichmentPipeline
from app.services.geospatial_enrichment import (
    PropertyGeospatialService,
    get_geocoding_coverage_summary,
)
from app.services.nearby_places import NearbyPlaceService, OverpassClient

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Build the geospatial enrichment command-line interface."""
    parser = argparse.ArgumentParser(description="Run resumable GeoEstate enrichment stages.")
    parser.add_argument(
        "--stage",
        choices=("all", *(stage.value for stage in EnrichmentStage)),
        default="all",
        help="Run all implemented stages or one named stage.",
    )
    parser.add_argument("--batch-size", type=int, default=None, help="Properties per transaction batch.")
    parser.add_argument(
        "--retry-failed-cache",
        action="store_true",
        help="Re-query cached failed localities once; use after inspecting failure diagnostics.",
    )
    return parser


async def run(stage_name: str, batch_size: int | None, retry_failed_cache: bool) -> None:
    """Run implemented enrichment stages against PostgreSQL in committed batches."""
    settings = get_settings()
    effective_batch_size = batch_size or settings.enrichment_batch_size
    if effective_batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    stages = tuple(EnrichmentStage) if stage_name == "all" else (EnrichmentStage(stage_name),)

    async with AsyncSessionFactory() as session:
        property_repository = PropertyRepository(session)
        cache_repository = GeocodeCacheRepository(session)
        needs_geocoding = EnrichmentStage.GEOCODE in stages
        needs_nearby = EnrichmentStage.NEARBY in stages
        if needs_geocoding or needs_nearby:
            async with AsyncExitStack() as stack:
                geocoding_client = (
                    await stack.enter_async_context(NominatimGeocodingClient(settings))
                    if needs_geocoding
                    else None
                )
                overpass_client = (
                    await stack.enter_async_context(OverpassClient(settings))
                    if needs_nearby
                    else None
                )
                pipeline = PropertyEnrichmentPipeline(
                    session,
                    property_repository,
                    batch_size=effective_batch_size,
                    progress_interval=settings.enrichment_progress_interval,
                    geospatial_service=(
                        PropertyGeospatialService(property_repository, cache_repository, geocoding_client)
                        if geocoding_client is not None else None
                    ),
                    nearby_place_service=(
                        NearbyPlaceService(NearbyPlaceCacheRepository(session), overpass_client, settings)
                        if overpass_client is not None else None
                    ),
                    retry_failed_cache=retry_failed_cache or settings.geocoding_retry_failed_cache,
                )
                summaries = await pipeline.run(stages)
        else:
            pipeline = PropertyEnrichmentPipeline(
                session,
                property_repository,
                batch_size=effective_batch_size,
                progress_interval=settings.enrichment_progress_interval,
            )
            summaries = await pipeline.run(stages)

        coverage = await get_geocoding_coverage_summary(
            property_repository,
            cache_repository,
        )

    for summary in summaries:
        LOGGER.info(
            "enrichment_stage_complete stage=%s properties_processed=%d properties_updated=%d provider_queries=%d cache_hits=%d failed_items=%d",
            summary.stage.value,
            summary.properties_processed,
            summary.properties_updated,
            summary.provider_queries,
            summary.cache_hits,
            summary.failed_localities,
        )
    LOGGER.info(
        "geocoding_coverage total_properties=%d geocoded=%d remaining=%d top_remaining_failed_localities=%s",
        coverage.total_properties,
        coverage.geocoded_properties,
        coverage.remaining_properties,
        [
            {
                "locality": entry.locality,
                "property_count": entry.property_count,
                "failure_reason": entry.failure_reason,
            }
            for entry in coverage.top_remaining_failed_localities
        ],
    )


def main() -> None:
    """Configure logging and run the async geospatial enrichment workflow."""
    configure_logging()
    arguments = build_parser().parse_args()
    asyncio.run(run(arguments.stage, arguments.batch_size, arguments.retry_failed_cache))


if __name__ == "__main__":
    main()
