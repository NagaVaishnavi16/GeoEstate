"""Unit tests ensuring locality aggregation retrieval remains database-side."""

import unittest

from sqlalchemy.dialects import postgresql

from app.repositories.locality_statistics import LocalityStatisticsRepository


class _ScalarsResult:
    def __iter__(self):
        return iter(())


class _Session:
    def __init__(self) -> None:
        self.statement = None

    async def scalar(self, statement):
        self.statement = statement
        return 0

    async def scalars(self, statement):
        self.statement = statement
        return _ScalarsResult()


class LocalityStatisticsRepositoryTests(unittest.IsolatedAsyncioTestCase):
    """Verify locality ordering and lookup predicates compile into SQL."""

    async def test_expensive_query_orders_average_price_descending(self) -> None:
        session = _Session()
        repository = LocalityStatisticsRepository(session)
        await repository.list_by_average_price(descending=True, limit=10)
        sql = str(session.statement.compile(dialect=postgresql.dialect()))
        self.assertIn("locality_statistics.average_price_lakh DESC", sql)

    async def test_exact_lookup_is_case_insensitive(self) -> None:
        session = _Session()
        repository = LocalityStatisticsRepository(session)
        await repository.get_by_locality("Gachibowli")
        sql = str(session.statement.compile(dialect=postgresql.dialect()))
        self.assertIn("lower(locality_statistics.locality)", sql)
