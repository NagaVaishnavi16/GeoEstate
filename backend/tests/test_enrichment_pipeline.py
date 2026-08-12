"""Unit tests for resumable Stage 1/2 pipeline batching and commits."""

import unittest
from types import SimpleNamespace
from decimal import Decimal

from app.services.enrichment_pipeline import EnrichmentStage, PropertyEnrichmentPipeline
from app.services.geospatial_enrichment import GeospatialEnrichmentSummary
from app.services.nearby_places import CategoryNearbyResult, NearbyPlace, NearbyPlaceEnrichment
from app.services.property_scoring import PropertyScoringService


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self.flushes = 0

    async def flush(self) -> None:
        self.flushes += 1

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
        self.nearby_batches = [[SimpleNamespace(property_id="hyd-3", latitude=1, longitude=1)], []]
        self.nearby_updates: list[str] = []
        self.targeted_nearby_batches: list[list[object]] = [[SimpleNamespace(property_id="hyd-target", latitude=1, longitude=1)]]
        self.score_batches = [
            [
                (
                    SimpleNamespace(
                        property_id="hyd-4",
                        rate_per_sqft=6000,
                        area_sqft=1500,
                        building_status="Ready to move",
                        nearest_metro_distance_m=100,
                        nearest_hospital_distance_m=100,
                        nearest_school_distance_m=100,
                        nearest_park_distance_m=100,
                        nearby_park_count=2,
                        nearest_metro="Metro",
                        nearest_hospital="Hospital",
                        nearest_school="School",
                        nearest_park="Park",
                    ),
                    6000,
                    1500,
                )
            ],
            [],
        ]
        self.score_updates: list[str] = []

    async def list_missing_coordinate_batch(self, **_: object) -> list[object]:
        return self.coordinate_batches.pop(0)

    async def list_missing_geometry_batch(self, **_: object) -> list[object]:
        return self.geometry_batches.pop(0)

    async def repair_missing_geometry(self, property_ids: list[str]) -> int:
        self.geometry_repairs.append(property_ids)
        return len(property_ids)

    async def list_missing_nearby_place_batch(self, **_: object) -> list[object]:
        return self.nearby_batches.pop(0)

    async def fill_missing_nearby_places(self, property_id: str, **_: object) -> int:
        self.nearby_updates.append(property_id)
        return 1

    async def list_missing_nearby_places_for_coordinates(self, coordinates: object) -> list[object]:
        self.targeted_coordinates = coordinates
        return self.targeted_nearby_batches.pop(0)

    async def list_missing_score_batch(self, **_: object) -> list[object]:
        return self.score_batches.pop(0)

    async def fill_missing_scores(self, property_id: str, **_: object) -> int:
        self.score_updates.append(property_id)
        return 1


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


class _FakeNearbyPlaceService:
    async def enrich_property(self, property_record: object) -> NearbyPlaceEnrichment:
        place = NearbyPlace("Test Metro", 100)
        empty = CategoryNearbyResult(None)
        return NearbyPlaceEnrichment(
            metro=CategoryNearbyResult(place),
            hospital=empty,
            school=empty,
            park=CategoryNearbyResult(None, park_count=0),
            cache_hits=4,
            provider_queries=0,
        )


class _InterruptedNearbyPlaceService:
    async def enrich_property(self, property_record: object) -> NearbyPlaceEnrichment:
        raise RuntimeError("simulated Overpass interruption")


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

    async def test_nearby_stage_commits_and_a_rerun_has_no_batch_to_process(self) -> None:
        session = _FakeSession()
        repository = _FakePropertyRepository()
        pipeline = PropertyEnrichmentPipeline(
            session,
            repository,
            batch_size=100,
            progress_interval=50,
            nearby_place_service=_FakeNearbyPlaceService(),
        )
        summaries = await pipeline.run((EnrichmentStage.NEARBY,))
        self.assertEqual(summaries[0].properties_updated, 1)
        self.assertEqual(session.commits, 1)
        self.assertEqual(session.flushes, 1)
        self.assertEqual(repository.nearby_updates, ["hyd-3"])

    async def test_nearby_stage_can_target_only_requested_coordinate_records(self) -> None:
        session = _FakeSession()
        repository = _FakePropertyRepository()
        repository.nearby_updates = []
        pipeline = PropertyEnrichmentPipeline(
            session,
            repository,
            batch_size=100,
            progress_interval=50,
            nearby_place_service=_FakeNearbyPlaceService(),
            nearby_coordinates=((Decimal("17.443622"), Decimal("78.351964")),),
        )
        summaries = await pipeline.run((EnrichmentStage.NEARBY,))
        self.assertEqual(summaries[0].properties_processed, 1)
        self.assertEqual(repository.nearby_updates, ["hyd-target"])
        self.assertEqual(repository.targeted_coordinates, ((Decimal("17.443622"), Decimal("78.351964")),))

    async def test_nearby_stage_rolls_back_then_can_resume_from_the_same_batch(self) -> None:
        session = _FakeSession()
        repository = _FakePropertyRepository()
        interrupted = PropertyEnrichmentPipeline(
            session,
            repository,
            batch_size=100,
            progress_interval=50,
            nearby_place_service=_InterruptedNearbyPlaceService(),
        )
        with self.assertRaisesRegex(RuntimeError, "interruption"):
            await interrupted.run((EnrichmentStage.NEARBY,))
        self.assertEqual(session.rollbacks, 1)

        repository.nearby_batches = [[SimpleNamespace(property_id="hyd-3", latitude=1, longitude=1)], []]
        resumed = PropertyEnrichmentPipeline(
            session,
            repository,
            batch_size=100,
            progress_interval=50,
            nearby_place_service=_FakeNearbyPlaceService(),
        )
        await resumed.run((EnrichmentStage.NEARBY,))
        self.assertEqual(repository.nearby_updates, ["hyd-3"])

    async def test_scoring_stage_commits_guarded_score_updates(self) -> None:
        session = _FakeSession()
        repository = _FakePropertyRepository()
        pipeline = PropertyEnrichmentPipeline(
            session,
            repository,
            batch_size=100,
            progress_interval=50,
            property_scoring_service=PropertyScoringService(),
        )
        summaries = await pipeline.run((EnrichmentStage.SCORING,))
        self.assertEqual(summaries[0].properties_processed, 1)
        self.assertEqual(summaries[0].properties_updated, 1)
        self.assertEqual(repository.score_updates, ["hyd-4"])
        self.assertEqual(session.commits, 1)
