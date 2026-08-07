"""Pydantic contracts for locality intelligence endpoints."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class LocalityEnrichmentResponse(BaseModel):
    """Aggregated availability and score information derived from enriched listings."""

    metro_available_listings: int = Field(ge=0)
    hospital_available_listings: int = Field(ge=0)
    school_available_listings: int = Field(ge=0)
    park_available_listings: int = Field(ge=0)
    average_metro_distance_m: Decimal | None = None
    average_hospital_distance_m: Decimal | None = None
    average_school_distance_m: Decimal | None = None
    average_park_distance_m: Decimal | None = None
    average_nearby_park_count: Decimal | None = None
    average_investment_score: Decimal | None = None
    average_connectivity_score: Decimal | None = None
    average_green_score: Decimal | None = None
    average_liveability_score: Decimal | None = None


class LocalityStatisticsResponse(BaseModel):
    """Current database-computed price, area, centroid, and enrichment analytics."""

    model_config = ConfigDict(from_attributes=True)

    locality: str
    total_listings: int = Field(ge=1)
    average_price_lakh: Decimal
    median_price_lakh: Decimal
    minimum_price_lakh: Decimal
    maximum_price_lakh: Decimal
    average_built_up_area_sqft: Decimal
    average_price_per_sqft: Decimal | None = None
    centroid_latitude: Decimal | None = None
    centroid_longitude: Decimal | None = None
    enrichment: LocalityEnrichmentResponse


class LocalityListResponse(BaseModel):
    """Stable pagination envelope for locality intelligence."""

    items: list[LocalityStatisticsResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
