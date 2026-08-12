"""Regression tests for nearby-place predicates in canonical property search."""

import unittest

from app.repositories.property import PropertyRepository
from app.services.search_types import PropertySearchCriteria


class _ScalarResult:
    def __init__(self, records: list[object]) -> None:
        self._records = records

    def __iter__(self):
        return iter(self._records)


class _Session:
    def __init__(self) -> None:
        self.data_statement = None

    async def scalar(self, statement):
        return 0

    async def scalars(self, statement):
        self.data_statement = statement
        return _ScalarResult([])


class PropertyRepositoryNearbyFilterTests(unittest.IsolatedAsyncioTestCase):
    """Ensure nearby search uses verified distance facts, not optional place labels."""

    async def test_near_metro_filters_on_computed_distance(self) -> None:
        session = _Session()
        repository = PropertyRepository(session)

        await repository.search(PropertySearchCriteria(near_metro=True))

        compiled = str(session.data_statement.compile(compile_kwargs={"literal_binds": True}))
        self.assertIn("nearest_metro_distance_m IS NOT NULL", compiled)
        self.assertNotIn("nearest_metro IS NOT NULL", compiled)
