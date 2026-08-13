"""Reusable FastAPI dependency providers."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.core.config import get_settings
from app.repositories.property import PropertyRepository
from app.repositories.market_insights import MarketInsightsRepository
from app.repositories.locality_statistics import LocalityStatisticsRepository
from app.services.locality_intelligence import LocalityIntelligenceService
from app.services.gemini_parser import GeminiParser
from app.services.natural_language_search import NaturalLanguageSearchService
from app.services.property import PropertyService
from app.services.search import PropertySearchService
from app.services.market_insights import MarketInsightsService


async def get_property_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> PropertyService:
    """Construct a request-scoped property service with its repository dependency."""
    return PropertyService(PropertyRepository(session))


async def get_property_search_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PropertySearchService:
    """Construct the shared search service independently of the calling transport."""
    return PropertySearchService(PropertyRepository(session))


async def get_locality_intelligence_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LocalityIntelligenceService:
    """Construct the request-scoped locality intelligence service."""
    return LocalityIntelligenceService(LocalityStatisticsRepository(session))


async def get_natural_language_search_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> NaturalLanguageSearchService:
    """Build the parser plus existing search-service composition for natural search."""
    return NaturalLanguageSearchService(
        GeminiParser(get_settings()),
        PropertySearchService(PropertyRepository(session)),
    )


async def get_market_insights_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MarketInsightsService:
    """Construct a request-scoped service for read-only frontend analytics."""
    return MarketInsightsService(MarketInsightsRepository(session))
