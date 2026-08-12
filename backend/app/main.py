"""FastAPI application factory and top-level route registration."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1.properties import router as properties_router
from app.api.v1.search import router as search_router
from app.api.v1.localities import router as localities_router
from app.api.v1.natural_search import router as natural_search_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import engine

LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Configure process resources and dispose database connections cleanly."""
    configure_logging()
    LOGGER.info("Starting GeoEstate API")
    try:
        yield
    finally:
        await engine.dispose()
        LOGGER.info("Stopped GeoEstate API")


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    description="Read-only property API for GeoEstate Intelligence.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_cors_origins,
    allow_credentials=False,
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)
app.include_router(health_router)
app.include_router(properties_router)
app.include_router(search_router)
app.include_router(localities_router)
app.include_router(natural_search_router)


@app.middleware("http")
async def log_request(request: Request, call_next) -> Response:
    """Emit one concise access-log event per completed HTTP request."""
    started_at = perf_counter()
    response = await call_next(request)
    LOGGER.info(
        "request_completed method=%s path=%s status=%d duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        (perf_counter() - started_at) * 1000,
    )
    return response
