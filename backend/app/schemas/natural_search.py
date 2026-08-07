"""Strict contracts for AI-extracted property-search filters and responses."""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.property import PropertyResponse
from app.services.search_types import PropertySortField, SortOrder


class NearbyIntentFilters(BaseModel):
    """Explicit nearby-place requirements extracted from natural language."""

    model_config = ConfigDict(extra="forbid")

    metro: bool = False
    hospital: bool = False
    school: bool = False
    park: bool = False


class ExtractedPropertyFilters(BaseModel):
    """Strict Gemini output contract; values are filters, never database commands."""

    model_config = ConfigDict(extra="forbid")

    property_type: str | None = Field(default=None, max_length=100)
    bhk: int | None = Field(default=None, ge=0, le=99)
    locality: str | None = Field(default=None, max_length=255)
    price_min: Decimal | None = Field(default=None, ge=0)
    price_max: Decimal | None = Field(default=None, ge=0)
    area_min: int | None = Field(default=None, gt=0)
    area_max: int | None = Field(default=None, gt=0)
    building_status: str | None = Field(default=None, max_length=100)
    nearby: NearbyIntentFilters = Field(default_factory=NearbyIntentFilters)
    sort_by: PropertySortField = PropertySortField.PRICE
    sort_order: SortOrder = SortOrder.ASC
    needs_clarification: bool = False
    clarification_message: str | None = Field(default=None, max_length=500)
    missing_fields: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_ranges_and_clarification(self) -> "ExtractedPropertyFilters":
        """Reject inverted bounds and incomplete clarification payloads."""
        if self.price_min is not None and self.price_max is not None and self.price_min > self.price_max:
            raise ValueError("price_min must not exceed price_max")
        if self.area_min is not None and self.area_max is not None and self.area_min > self.area_max:
            raise ValueError("area_min must not exceed area_max")
        if self.needs_clarification and (not self.clarification_message or not self.missing_fields):
            raise ValueError("clarification responses require a message and missing_fields")
        return self


class NaturalSearchRequest(BaseModel):
    """Natural-language property search input."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "query": "Show me 3 BHK apartments under 1 crore in Gachibowli near metro",
                    "limit": 20,
                    "offset": 0,
                }
            ]
        },
    )

    query: str = Field(min_length=1, max_length=1_000)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class NaturalSearchSuccessResponse(BaseModel):
    """Validated intent and results returned through the existing search service."""

    status: Literal["completed"] = "completed"
    query: str
    extracted_filters: ExtractedPropertyFilters
    results: list[PropertyResponse]
    total_results: int = Field(ge=0)


class NaturalSearchClarificationResponse(BaseModel):
    """Response returned when the model identifies missing critical constraints."""

    status: Literal["needs_clarification"] = "needs_clarification"
    message: str
    missing_fields: list[str]


class NaturalSearchValidationResponse(BaseModel):
    """Safe response returned when provider output cannot pass strict validation."""

    status: Literal["validation_error"] = "validation_error"
    message: str
    errors: list[str] = Field(default_factory=list)


NaturalSearchResponse = Annotated[
    NaturalSearchSuccessResponse | NaturalSearchClarificationResponse | NaturalSearchValidationResponse,
    Field(discriminator="status"),
]
