"""Read-only descriptive analytics contracts for the GeoEstate frontend."""

from decimal import Decimal

from pydantic import BaseModel, Field


class PriceDistributionResponse(BaseModel):
    """Citywide distribution of listings with a verified price per square foot."""

    listing_count: int = Field(ge=0)
    minimum: Decimal | None = None
    first_quartile: Decimal | None = None
    median: Decimal | None = None
    third_quartile: Decimal | None = None
    maximum: Decimal | None = None


class LocalityPriceMetricResponse(BaseModel):
    """Price and rate summary for a locality with usable rate data."""

    locality: str
    total_listings: int = Field(ge=1)
    average_price_lakh: Decimal
    median_price_lakh: Decimal
    average_price_per_sqft: Decimal


class ScorePriceMetricResponse(BaseModel):
    """Descriptive score coverage and price summary, never a causal claim."""

    score: str
    scored_listings: int = Field(ge=0)
    average_score: Decimal | None = None
    average_price_lakh: Decimal | None = None
    average_price_per_sqft: Decimal | None = None


class PriceRateOutlierResponse(BaseModel):
    """A listing rate compared with its current locality average rate."""

    property_id: str
    locality: str
    price_lakh: Decimal
    rate_per_sqft: Decimal
    locality_average_price_per_sqft: Decimal
    rate_to_locality_average: Decimal


class AmenityPriceMetricResponse(BaseModel):
    """Availability and pricing of records with a verified nearby amenity distance."""

    amenity: str
    listings_with_verified_distance: int = Field(ge=0)
    average_price_lakh: Decimal | None = None
    average_price_per_sqft: Decimal | None = None
    average_distance_m: Decimal | None = None


class InsightStatementResponse(BaseModel):
    """A concise, data-derived descriptive statement for the interface."""

    text: str


class MarketInsightsResponse(BaseModel):
    """Small, database-backed analytics payload for the existing search experience."""

    price_per_sqft_distribution: PriceDistributionResponse
    locality_price_metrics: list[LocalityPriceMetricResponse]
    score_price_metrics: list[ScorePriceMetricResponse]
    rate_outliers: list[PriceRateOutlierResponse]
    amenity_price_metrics: list[AmenityPriceMetricResponse]
    statements: list[InsightStatementResponse] = Field(max_length=4)
