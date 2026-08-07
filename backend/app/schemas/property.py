"""Pydantic v2 schemas for the property API boundary."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.search_types import PropertySortField, SortOrder


class PropertyBase(BaseModel):
    """Shared validated representation of the processed property dataset."""

    property_id: str = Field(min_length=1, max_length=24)
    title: str = Field(default="", max_length=255)
    location: str = Field(min_length=1, max_length=255)
    price_lakh: Decimal = Field(max_digits=14, decimal_places=2)
    rate_per_sqft: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    area_sqft: int = Field(gt=0)
    building_status: str = Field(default="", max_length=100)
    bedrooms: int | None = Field(default=None, ge=0, le=99)

    latitude: Decimal | None = Field(default=None, ge=15.8, le=19.9, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=77, le=81.3, max_digits=9, decimal_places=6)
    investment_score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    connectivity_score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    green_score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    liveability_score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    nearest_metro: str | None = Field(default=None, max_length=255)
    nearest_hospital: str | None = Field(default=None, max_length=255)
    nearest_school: str | None = Field(default=None, max_length=255)
    nearest_park: str | None = Field(default=None, max_length=255)
    nearest_metro_distance_m: int | None = Field(default=None, ge=0)
    nearest_hospital_distance_m: int | None = Field(default=None, ge=0)
    nearest_school_distance_m: int | None = Field(default=None, ge=0)
    nearest_park_distance_m: int | None = Field(default=None, ge=0)
    nearby_park_count: int | None = Field(default=None, ge=0)
    ai_summary: str | None = None


class PropertyCreate(PropertyBase):
    """Validated write contract retained for the CSV importer and future CRUD."""


class PropertyUpdate(BaseModel):
    """Partial update contract for future internal workflows; not exposed in Phase 1."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    price_lakh: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    rate_per_sqft: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    area_sqft: int | None = Field(default=None, gt=0)
    building_status: str | None = Field(default=None, max_length=100)
    bedrooms: int | None = Field(default=None, ge=0, le=99)
    latitude: Decimal | None = Field(default=None, ge=15.8, le=19.9, max_digits=9, decimal_places=6)
    longitude: Decimal | None = Field(default=None, ge=77, le=81.3, max_digits=9, decimal_places=6)
    investment_score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    connectivity_score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    green_score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    liveability_score: Decimal | None = Field(default=None, ge=0, le=100, max_digits=5, decimal_places=2)
    nearest_metro: str | None = Field(default=None, max_length=255)
    nearest_hospital: str | None = Field(default=None, max_length=255)
    nearest_school: str | None = Field(default=None, max_length=255)
    nearest_park: str | None = Field(default=None, max_length=255)
    nearest_metro_distance_m: int | None = Field(default=None, ge=0)
    nearest_hospital_distance_m: int | None = Field(default=None, ge=0)
    nearest_school_distance_m: int | None = Field(default=None, ge=0)
    nearest_park_distance_m: int | None = Field(default=None, ge=0)
    nearby_park_count: int | None = Field(default=None, ge=0)
    ai_summary: str | None = None


class PropertyResponse(PropertyBase):
    """Public read contract for a persisted property."""

    model_config = ConfigDict(from_attributes=True)


class PropertyListResponse(BaseModel):
    """Stable offset-pagination response returned by the property list endpoint."""

    items: list[PropertyResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class PropertySearchRequest(BaseModel):
    """HTTP input contract for the shared geospatial-aware property search service."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "location": "Gachibowli",
                    "min_price": 5_000_000,
                    "max_price": 9_000_000,
                    "bedrooms": 3,
                    "near_metro": True,
                    "limit": 20,
                    "offset": 0,
                    "sort_by": "price",
                    "sort_order": "asc",
                }
            ]
        },
    )

    location: str | None = Field(default=None, min_length=1, max_length=255)
    min_price: Decimal | None = Field(default=None, ge=0, description="Minimum price in INR.")
    max_price: Decimal | None = Field(default=None, ge=0, description="Maximum price in INR.")
    bedrooms: int | None = Field(default=None, ge=0, le=99)
    min_area: int | None = Field(default=None, gt=0, description="Minimum area in square feet.")
    max_area: int | None = Field(default=None, gt=0, description="Maximum area in square feet.")
    property_type: str | None = Field(default=None, min_length=1, max_length=100)
    building_status: str | None = Field(default=None, min_length=1, max_length=100)
    near_metro: bool = False
    near_hospital: bool = False
    near_school: bool = False
    near_park: bool = False
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    sort_by: PropertySortField = PropertySortField.PRICE
    sort_order: SortOrder = SortOrder.ASC

    @model_validator(mode="after")
    def validate_ranges(self) -> "PropertySearchRequest":
        """Reject inverted price and area ranges before reaching the service layer."""
        if self.min_price is not None and self.max_price is not None and self.min_price > self.max_price:
            raise ValueError("min_price must not exceed max_price")
        if self.min_area is not None and self.max_area is not None and self.min_area > self.max_area:
            raise ValueError("min_area must not exceed max_area")
        return self


class CoordinatesResponse(BaseModel):
    """Explicit coordinate subdocument for detailed property retrieval."""

    latitude: Decimal | None = None
    longitude: Decimal | None = None


class FutureIntelligenceResponse(BaseModel):
    """Stable extension point for planned intelligence outputs."""

    investment_score: Decimal | None = None
    ai_summary: str | None = None
    nearest_school: str | None = None
    nearest_hospital: str | None = None
    nearest_metro: str | None = None
    nearest_park: str | None = None
    nearest_metro_distance_m: int | None = None
    nearest_hospital_distance_m: int | None = None
    nearest_school_distance_m: int | None = None
    nearest_park_distance_m: int | None = None
    nearby_park_count: int | None = None
    green_score: Decimal | None = None
    satellite_analysis: dict[str, object] | None = None


class PropertyDetailsResponse(BaseModel):
    """Extensible property detail document that preserves a stable future API shape."""

    property: PropertyResponse
    coordinates: CoordinatesResponse
    future_intelligence: FutureIntelligenceResponse
