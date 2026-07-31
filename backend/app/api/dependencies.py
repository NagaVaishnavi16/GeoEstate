"""Reusable FastAPI dependency providers."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.property import PropertyRepository
from app.services.property import PropertyService
from app.services.search import PropertySearchService


async def get_property_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> PropertyService:
    """Construct a request-scoped property service with its repository dependency."""
    return PropertyService(PropertyRepository(session))


async def get_property_search_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PropertySearchService:
    """Construct the shared search service independently of the calling transport."""
    return PropertySearchService(PropertyRepository(session))
