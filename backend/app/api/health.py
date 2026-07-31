"""Operational health endpoint."""

from typing import Annotated

import logging

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])
LOGGER = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse, summary="Check API and database health")
async def health_check(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> HealthResponse:
    """Return API, database, and PostGIS readiness in one stable response contract."""
    settings = get_settings()
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        LOGGER.warning("Health check database failure: %s", error)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", database=False, postgis=False, version=settings.api_version)
    try:
        await session.execute(text("SELECT PostGIS_Version()"))
    except SQLAlchemyError as error:
        LOGGER.warning("Health check PostGIS failure: %s", error)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="degraded", database=True, postgis=False, version=settings.api_version)
    return HealthResponse(status="ok", database=True, postgis=True, version=settings.api_version)
