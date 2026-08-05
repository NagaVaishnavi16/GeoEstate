"""Unit tests for repository-only nearby-place selection and guarded updates."""

import unittest
from sqlalchemy.dialects import postgresql

from app.repositories.property import PropertyRepository


class _ScalarResult:
    def __iter__(self):
        return iter(())


class _CapturingSession:
    def __init__(self) -> None:
        self.statement = None

    async def scalars(self, statement):
        self.statement = statement
        return _ScalarResult()

    async def execute(self, statement):
        self.statement = statement
        return type("Result", (), {"rowcount": 1})()


class NearbyPlaceRepositoryTests(unittest.IsolatedAsyncioTestCase):
    """Verify required SQL predicates are contained inside the repository."""

    async def test_selector_requires_coordinates_and_missing_nearby_field(self) -> None:
        session = _CapturingSession()
        repository = PropertyRepository(session)
        await repository.list_missing_nearby_place_batch(after_property_id="hyd-001", batch_size=100)
        sql = str(session.statement.compile(dialect=postgresql.dialect()))
        self.assertIn("properties.latitude IS NOT NULL", sql)
        self.assertIn("properties.nearby_park_count IS NULL", sql)
        self.assertIn("properties.property_id >", sql)

    async def test_update_uses_null_guard_and_coalesce(self) -> None:
        session = _CapturingSession()
        repository = PropertyRepository(session)
        count = await repository.fill_missing_nearby_places(
            "hyd-001",
            nearest_metro="Raidurg Metro",
            nearest_metro_distance_m=320,
            nearest_hospital=None,
            nearest_hospital_distance_m=None,
            nearest_school=None,
            nearest_school_distance_m=None,
            nearest_park=None,
            nearest_park_distance_m=None,
            nearby_park_count=2,
        )
        sql = str(session.statement.compile(dialect=postgresql.dialect()))
        self.assertEqual(count, 1)
        self.assertIn("coalesce(properties.nearest_metro", sql)
        self.assertIn("properties.nearby_park_count IS NULL", sql)
