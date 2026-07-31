"""Pipeline orchestration and CSV input/output for GeoEstate."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .cleaning import add_placeholder_columns, create_property_ids, derive_bedrooms, normalize_values, remove_business_duplicates, standardize_columns, validate_and_filter
from .config import PipelineConfig

LOGGER = logging.getLogger(__name__)


def preprocess_dataframe(raw_frame: pd.DataFrame, config: PipelineConfig | None = None) -> pd.DataFrame:
    """Transform a raw property dataframe into the GeoEstate canonical schema."""
    active_config = config or PipelineConfig()
    initial_rows = len(raw_frame)
    frame = standardize_columns(raw_frame)
    frame = normalize_values(frame)
    frame = derive_bedrooms(frame)
    frame = validate_and_filter(frame, active_config)
    filtered_rows = len(frame)
    frame = remove_business_duplicates(frame, active_config)
    frame.insert(0, "property_id", create_property_ids(frame))
    frame = add_placeholder_columns(frame).reset_index(drop=True)
    LOGGER.info("Preprocessing complete: input_rows=%d, invalid_rows_removed=%d, duplicate_rows_removed=%d, output_rows=%d", initial_rows, initial_rows - filtered_rows, filtered_rows - len(frame), len(frame))
    return frame


def preprocess_file(input_path: Path, output_path: Path, config: PipelineConfig | None = None) -> pd.DataFrame:
    """Read a raw CSV, preprocess it, and persist the canonical CSV output."""
    LOGGER.info("Reading raw dataset: %s", input_path)
    processed = preprocess_dataframe(pd.read_csv(input_path), config=config)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed.to_csv(output_path, index=False)
    LOGGER.info("Wrote processed dataset: %s", output_path)
    return processed
