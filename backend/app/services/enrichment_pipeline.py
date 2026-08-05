"""Resumable orchestration for the completed enrichment stages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.property import PropertyRepository
from app.services.geospatial_enrichment import PropertyGeospatialService
from app.services.nearby_places import NearbyPlaceEnrichment, NearbyPlaceService

LOGGER = logging.getLogger(__name__)


class EnrichmentStage(StrEnum):
    """Stages currently implemented by the production enrichment pipeline."""

    GEOCODE = "geocode"
    GEOMETRY = "geometry"
    NEARBY = "nearby"


@dataclass(frozen=True)
class StageRunSummary:
    """Outcome of one resumable enrichment stage."""

    stage: EnrichmentStage
    properties_processed: int
    properties_updated: int
    provider_queries: int = 0
    cache_hits: int = 0
    failed_localities: int = 0


class PropertyEnrichmentPipeline:
    """Run non-destructive enrichment stages in committed, cursor-based batches."""

    def __init__(
        self,
        session: AsyncSession,
        property_repository: PropertyRepository,
        *,
        batch_size: int,
        progress_interval: int,
        geospatial_service: PropertyGeospatialService | None = None,
        nearby_place_service: NearbyPlaceService | None = None,
        retry_failed_cache: bool = False,
    ) -> None:
        self._session = session
        self._property_repository = property_repository
        self._batch_size = batch_size
        self._progress_interval = progress_interval
        self._geospatial_service = geospatial_service
        self._nearby_place_service = nearby_place_service
        self._retry_failed_cache = retry_failed_cache

    async def run(self, stages: tuple[EnrichmentStage, ...]) -> list[StageRunSummary]:
        """Run requested stages in order and return independent stage summaries."""
        summaries: list[StageRunSummary] = []
        for stage in stages:
            if stage is EnrichmentStage.GEOCODE:
                summaries.append(await self._run_geocode_stage())
            elif stage is EnrichmentStage.GEOMETRY:
                summaries.append(await self._run_geometry_stage())
            elif stage is EnrichmentStage.NEARBY:
                summaries.append(await self._run_nearby_stage())
        return summaries

    async def _run_geocode_stage(self) -> StageRunSummary:
        """Fill only missing property coordinates through the cached locality geocoder."""
        if self._geospatial_service is None:
            raise RuntimeError("Geocoding stage requires a configured PropertyGeospatialService")

        cursor: str | None = None
        processed = updated = provider_queries = cache_hits = failed_localities = 0
        next_progress_log = self._progress_interval
        while True:
            batch = await self._property_repository.list_missing_coordinate_batch(
                after_property_id=cursor,
                batch_size=self._batch_size,
            )
            if not batch:
                break
            cursor = batch[-1].property_id
            try:
                _, summary = await self._geospatial_service.enrich_localities(
                    (property_record.location for property_record in batch),
                    retry_failed_cache=self._retry_failed_cache,
                )
                await self._session.commit()
            except Exception:
                await self._session.rollback()
                raise

            processed += len(batch)
            updated += summary.properties_updated
            provider_queries += summary.provider_queries
            cache_hits += summary.cache_hits
            failed_localities += summary.failed_localities
            next_progress_log = self._log_progress(
                EnrichmentStage.GEOCODE,
                processed,
                updated,
                next_progress_log,
            )

        return StageRunSummary(
            stage=EnrichmentStage.GEOCODE,
            properties_processed=processed,
            properties_updated=updated,
            provider_queries=provider_queries,
            cache_hits=cache_hits,
            failed_localities=failed_localities,
        )

    async def _run_geometry_stage(self) -> StageRunSummary:
        """Repair only geometry values absent despite complete source coordinates."""
        cursor: str | None = None
        processed = updated = 0
        next_progress_log = self._progress_interval
        while True:
            batch = await self._property_repository.list_missing_geometry_batch(
                after_property_id=cursor,
                batch_size=self._batch_size,
            )
            if not batch:
                break
            cursor = batch[-1].property_id
            try:
                updated_in_batch = await self._property_repository.repair_missing_geometry(
                    [property_record.property_id for property_record in batch]
                )
                await self._session.commit()
            except Exception:
                await self._session.rollback()
                raise

            processed += len(batch)
            updated += updated_in_batch
            next_progress_log = self._log_progress(
                EnrichmentStage.GEOMETRY,
                processed,
                updated,
                next_progress_log,
            )

        return StageRunSummary(
            stage=EnrichmentStage.GEOMETRY,
            properties_processed=processed,
            properties_updated=updated,
        )

    async def _run_nearby_stage(self) -> StageRunSummary:
        """Fill only missing nearby-place values from the cache-first Overpass service."""
        if self._nearby_place_service is None:
            raise RuntimeError("Nearby stage requires a configured NearbyPlaceService")
        cursor: str | None = None
        processed = updated = provider_queries = cache_hits = failed_requests = 0
        next_progress_log = self._progress_interval
        while True:
            batch = await self._property_repository.list_missing_nearby_place_batch(
                after_property_id=cursor,
                batch_size=self._batch_size,
            )
            if not batch:
                break
            cursor = batch[-1].property_id
            processed_in_batch = 0
            deferred = False
            try:
                for property_record in batch:
                    enrichment = await self._nearby_place_service.enrich_property(property_record)
                    if enrichment.deferred:
                        deferred = True
                        break
                    updated += await self._persist_nearby_result(property_record.property_id, enrichment)
                    provider_queries += enrichment.provider_queries
                    cache_hits += enrichment.cache_hits
                    processed_in_batch += 1
                await self._session.flush()
                await self._session.commit()
            except Exception:
                await self._session.rollback()
                failed_requests += 1
                raise
            processed += processed_in_batch
            next_progress_log = self._log_progress(
                EnrichmentStage.NEARBY,
                processed,
                updated,
                next_progress_log,
            )
            if deferred:
                self._nearby_place_service.log_resume_summary()
                break
        return StageRunSummary(
            stage=EnrichmentStage.NEARBY,
            properties_processed=processed,
            properties_updated=updated,
            provider_queries=provider_queries,
            cache_hits=cache_hits,
            failed_localities=failed_requests,
        )

    async def _persist_nearby_result(
        self,
        property_id: str,
        enrichment: NearbyPlaceEnrichment,
    ) -> int:
        """Delegate the guarded property update while keeping the service database-agnostic."""
        return await self._property_repository.fill_missing_nearby_places(
            property_id,
            nearest_metro=enrichment.metro.nearest.name if enrichment.metro.nearest else None,
            nearest_metro_distance_m=enrichment.metro.nearest.distance_m if enrichment.metro.nearest else None,
            nearest_hospital=enrichment.hospital.nearest.name if enrichment.hospital.nearest else None,
            nearest_hospital_distance_m=enrichment.hospital.nearest.distance_m if enrichment.hospital.nearest else None,
            nearest_school=enrichment.school.nearest.name if enrichment.school.nearest else None,
            nearest_school_distance_m=enrichment.school.nearest.distance_m if enrichment.school.nearest else None,
            nearest_park=enrichment.park.nearest.name if enrichment.park.nearest else None,
            nearest_park_distance_m=enrichment.park.nearest.distance_m if enrichment.park.nearest else None,
            nearby_park_count=enrichment.park.park_count,
        )

    def _log_progress(
        self,
        stage: EnrichmentStage,
        processed: int,
        updated: int,
        next_progress_log: int,
    ) -> int:
        """Emit progress at exact configured property-count intervals."""
        while processed >= next_progress_log:
            LOGGER.info(
                "enrichment_progress stage=%s properties_processed=%d properties_updated=%d",
                stage.value,
                next_progress_log,
                updated,
            )
            next_progress_log += self._progress_interval
        return next_progress_log
