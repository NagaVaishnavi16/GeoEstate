"""Pydantic request and response contracts."""

from .property import (
    PropertyCreate,
    PropertyDetailsResponse,
    PropertyListResponse,
    PropertyResponse,
    PropertySearchRequest,
    PropertyUpdate,
)
from .locality import LocalityListResponse, LocalityStatisticsResponse
from .natural_search import NaturalSearchRequest, NaturalSearchResponse

__all__ = [
    "PropertyCreate",
    "PropertyDetailsResponse",
    "PropertyListResponse",
    "PropertyResponse",
    "PropertySearchRequest",
    "PropertyUpdate",
    "LocalityListResponse",
    "LocalityStatisticsResponse",
    "NaturalSearchRequest",
    "NaturalSearchResponse",
]
