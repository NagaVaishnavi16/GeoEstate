"""Business service for public property retrieval."""

from typing import List

from app.models.property import Property
from app.repositories.property import PropertyRepository


class PropertyService:
    """Coordinate property retrieval without exposing persistence to API routes."""

    def __init__(self, repository: PropertyRepository) -> None:
        self._repository = repository

    async def list_properties(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[List[Property], int]:
        """Return a page of canonical property listings."""
        return await self._repository.list_properties(
            limit=limit,
            offset=offset,
        )

    async def get_property(self, property_id: str) -> Property | None:
        """Retrieve a listing by its external property identifier."""
        return await self._repository.get_by_id(property_id)

    async def get_property_details(self, property_id: str) -> Property | None:
        """Retrieve a property for the extensible detail representation."""
        return await self._repository.get_by_id(property_id)
