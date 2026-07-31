"""Pure, reusable transformations for property-listing data."""

from __future__ import annotations

import hashlib
import re

import pandas as pd

from .config import COLUMN_ALIASES, NUMERIC_COLUMNS, PLACEHOLDER_COLUMNS, TEXT_COLUMNS, PipelineConfig
from .exceptions import SchemaError


def to_snake_case(column_name: object) -> str:
    """Convert a source header into a predictable snake_case identifier."""
    value = str(column_name).strip()
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value).lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def standardize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop CSV export indexes and normalize recognized source headers."""
    cleaned = frame.copy()
    cleaned = cleaned.loc[:, ~cleaned.columns.astype(str).str.match(r"^unnamed", case=False)]
    renamed = {column: COLUMN_ALIASES.get(to_snake_case(column), to_snake_case(column)) for column in cleaned.columns}
    cleaned = cleaned.rename(columns=renamed)
    if cleaned.columns.duplicated().any():
        duplicates = cleaned.columns[cleaned.columns.duplicated()].tolist()
        raise SchemaError(f"Column aliases produced duplicate columns: {duplicates}")
    return cleaned


def clean_text(value: object) -> object:
    """Strip and collapse whitespace, preserving missing values."""
    if pd.isna(value):
        return pd.NA
    normalized = re.sub(r"\s+", " ", str(value)).strip()
    return normalized if normalized else pd.NA


def normalize_values(frame: pd.DataFrame) -> pd.DataFrame:
    """Clean text and coerce known numeric fields to nullable numeric dtypes."""
    cleaned = frame.copy()
    for column in TEXT_COLUMNS:
        if column in cleaned:
            cleaned[column] = cleaned[column].map(clean_text).astype("string")
    for column in NUMERIC_COLUMNS:
        if column in cleaned:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    return cleaned


def derive_bedrooms(frame: pd.DataFrame) -> pd.DataFrame:
    """Fill missing bedroom counts from listing titles such as '3 BHK Apartment'."""
    cleaned = frame.copy()
    if "bedrooms" not in cleaned:
        cleaned["bedrooms"] = pd.NA
    if "title" in cleaned:
        extracted = cleaned["title"].astype("string").str.extract(r"(?i)\b(\d+)\s*(?:bhk|bed(?:room)?s?)\b", expand=False)
        cleaned["bedrooms"] = cleaned["bedrooms"].fillna(pd.to_numeric(extracted, errors="coerce"))
    cleaned["bedrooms"] = pd.to_numeric(cleaned["bedrooms"], errors="coerce").astype("Int64")
    return cleaned


def validate_and_filter(frame: pd.DataFrame, config: PipelineConfig) -> pd.DataFrame:
    """Check required columns and remove rows without valid core property data."""
    missing = [column for column in config.required_columns if column not in frame]
    if missing:
        raise SchemaError(f"Input is missing required columns after standardization: {missing}")
    valid = frame["location"].notna() & frame["price_lakh"].gt(0) & frame["area_sqft"].gt(0)
    return frame.loc[valid].copy()


def remove_business_duplicates(frame: pd.DataFrame, config: PipelineConfig) -> pd.DataFrame:
    """Remove exact duplicate listings using only columns present in the input."""
    subset = [column for column in config.deduplication_columns if column in frame]
    return frame.drop_duplicates(subset=subset, keep="first").copy()


def create_property_ids(frame: pd.DataFrame) -> pd.Series:
    """Create deterministic unique identifiers from canonical listing content."""
    id_columns = [column for column in frame.columns if column != "property_id"]
    signatures = frame[id_columns].astype("string").fillna("<NULL>").agg("|".join, axis=1)
    occurrences = signatures.groupby(signatures, sort=False).cumcount().astype(str)
    return (signatures + "|" + occurrences).map(
        lambda value: f"hyd-{hashlib.sha256(value.encode('utf-8')).hexdigest()[:20]}"
    ).astype("string")


def add_placeholder_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Add typed null columns reserved for future enrichment stages."""
    enriched = frame.copy()
    numeric_placeholders = {"latitude", "longitude", "investment_score", "connectivity_score", "green_score", "liveability_score"}
    for column in PLACEHOLDER_COLUMNS:
        if column not in enriched:
            dtype = "Float64" if column in numeric_placeholders else "string"
            enriched[column] = pd.Series(pd.NA, index=enriched.index, dtype=dtype)
    return enriched
