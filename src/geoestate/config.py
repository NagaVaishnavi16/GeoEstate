"""Schema and configuration constants for preprocessing."""

from dataclasses import dataclass


COLUMN_ALIASES: dict[str, str] = {
    "price_l": "price_lakh", "price_lakh": "price_lakh", "price": "price_lakh",
    "rate_persqft": "rate_per_sqft", "rate_per_sqft": "rate_per_sqft",
    "area": "area_sqft", "area_insqft": "area_sqft", "area_in_sqft": "area_sqft",
    "no_of_bedrooms": "bedrooms", "no_bedrooms": "bedrooms", "buildingstatus": "building_status",
}
NUMERIC_COLUMNS: tuple[str, ...] = ("price_lakh", "rate_per_sqft", "area_sqft", "bedrooms")
TEXT_COLUMNS: tuple[str, ...] = ("title", "location", "building_status")
PLACEHOLDER_COLUMNS: tuple[str, ...] = (
    "latitude", "longitude", "investment_score", "connectivity_score", "green_score",
    "liveability_score", "nearest_metro", "nearest_hospital", "nearest_school", "ai_summary",
)


@dataclass(frozen=True)
class PipelineConfig:
    """Controls quality gates used by the preprocessing pipeline."""

    required_columns: tuple[str, ...] = ("location", "price_lakh", "area_sqft")
    deduplication_columns: tuple[str, ...] = (
        "title", "location", "price_lakh", "rate_per_sqft", "area_sqft", "building_status", "bedrooms",
    )
