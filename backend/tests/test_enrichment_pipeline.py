"""Unit tests for resumable Stage 1/2 pipeline batching and commits."""

import unittest
from types import SimpleNamespace

from app.services.enrichment_pipeline import EnrichmentStage, PropertyEnrichmentPipeline
from app.services.geospatial_enrichment import GeospatialEnrichmentSummary


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class _FakePropertyRepository:
    def __init__(self) -> None:
        self.coordinate_batches = [
            [SimpleNamespace(property_id="hyd-1", location="Ameerpet")],
            [],
        ]
        self.geometry_batches = [
            [SimpleNamespace(property_id="hyd-2", location="Banjara Hills")],
            [],
        ]
        self.geometry_repairs: list[list[str]] = []

    async def list_missing_coordinate_batch(self, **_: object) -> list[object]:
        return self.coordinate_batches.pop(0)

    async def list_missing_geometry_batch(self, **_: object) -> list[object]:
        return self.geometry_batches.pop(0)

    async def repair_missing_geometry(self, property_ids: list[str]) -> int:
        self.geometry_repairs.append(property_ids)
        return len(property_ids)


class _FakeGeospatialService:
    async def enrich_localities(self, localities, *, retry_failed_cache: bool = False):
        list(localities)
        return [], GeospatialEnrichmentSummary(
            total_localities=1,
            cache_hits=1,
            provider_queries=0,
            successful_localities=1,
            failed_localities=0,
            properties_updated=1,
        )


class PropertyEnrichmentPipelineTests(unittest.IsolatedAsyncioTestCase):
    """Verify batches commit independently and completed records are not revisited."""

    async def test_geocode_and_geometry_stages_commit_each_batch(self) -> None:
        session = _FakeSession()
        repository = _FakePropertyRepository()
        pipeline = PropertyEnrichmentPipeline(
            session,
            repository,
            batch_size=100,
            progress_interval=50,
            geospatial_service=_FakeGeospatialService(),
        )

        summaries = await pipeline.run((EnrichmentStage.GEOCODE, EnrichmentStage.GEOMETRY))

        self.assertEqual(session.commits, 2)
        self.assertEqual(summaries[0].properties_updated, 1)
        self.assertEqual(summaries[1].properties_updated, 1)
        self.assertEqual(repository.geometry_repairs, [["hyd-2"]])
