"""Application services for importing canonical property data."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator

from django.db import transaction
from django.utils import timezone

from .models import Property

REQUIRED_CSV_COLUMNS = frozenset({"property_id", "location", "price_lakh", "area_sqft"})
UPSERT_FIELDS = (
    "title", "location", "price_lakh", "rate_per_sqft", "area_sqft", "building_status", "bedrooms",
    "latitude", "longitude", "investment_score", "connectivity_score", "green_score", "liveability_score",
    "nearest_metro", "nearest_hospital", "nearest_school", "ai_summary", "updated_at",
)


class PropertyImportError(ValueError):
    """Raised when a processed property CSV cannot be imported safely."""


@dataclass(frozen=True)
class ImportResult:
    """Summary returned after an idempotent property import."""

    rows_processed: int
    source_path: Path


class PropertyImportService:
    """Load canonical property CSV records into PostgreSQL in upsert batches."""

    def __init__(self, source_path: Path, batch_size: int = 500) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self.source_path = source_path
        self.batch_size = batch_size

    def import_data(self) -> ImportResult:
        """Upsert every row from the processed CSV in a single transaction."""
        if not self.source_path.is_file():
            raise PropertyImportError(f"Processed CSV does not exist: {self.source_path}")

        rows_processed = 0
        with self.source_path.open("r", encoding="utf-8-sig", newline="") as source_file:
            reader = csv.DictReader(source_file)
            self._validate_headers(reader.fieldnames)
            with transaction.atomic():
                for batch in self._batches(reader):
                    Property.objects.bulk_create(
                        batch,
                        batch_size=self.batch_size,
                        update_conflicts=True,
                        update_fields=UPSERT_FIELDS,
                        unique_fields=["property_id"],
                    )
                    rows_processed += len(batch)
        return ImportResult(rows_processed=rows_processed, source_path=self.source_path)

    def _batches(self, reader: csv.DictReader) -> Iterator[list[Property]]:
        """Create database-sized batches while retaining row-numbered failures."""
        batch: list[Property] = []
        for row_number, row in enumerate(reader, start=2):
            batch.append(self._build_property(row, row_number))
            if len(batch) == self.batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    @staticmethod
    def _validate_headers(fieldnames: list[str] | None) -> None:
        available = set(fieldnames or [])
        missing = sorted(REQUIRED_CSV_COLUMNS - available)
        if missing:
            raise PropertyImportError(f"CSV is missing required columns: {', '.join(missing)}")

    @staticmethod
    def _build_property(row: dict[str, str], row_number: int) -> Property:
        """Map a CSV row into a Property instance with strict type conversion."""
        try:
            now = timezone.now()
            return Property(
                property_id=PropertyImportService._required_text(row, "property_id", row_number),
                title=PropertyImportService._text(row.get("title")) or "",
                location=PropertyImportService._required_text(row, "location", row_number),
                price_lakh=PropertyImportService._decimal(row.get("price_lakh"), "price_lakh", row_number),
                rate_per_sqft=PropertyImportService._optional_decimal(row.get("rate_per_sqft"), "rate_per_sqft", row_number),
                area_sqft=PropertyImportService._integer(row.get("area_sqft"), "area_sqft", row_number),
                building_status=PropertyImportService._text(row.get("building_status")) or "",
                bedrooms=PropertyImportService._optional_integer(row.get("bedrooms"), "bedrooms", row_number),
                latitude=PropertyImportService._optional_decimal(row.get("latitude"), "latitude", row_number),
                longitude=PropertyImportService._optional_decimal(row.get("longitude"), "longitude", row_number),
                investment_score=PropertyImportService._optional_decimal(row.get("investment_score"), "investment_score", row_number),
                connectivity_score=PropertyImportService._optional_decimal(row.get("connectivity_score"), "connectivity_score", row_number),
                green_score=PropertyImportService._optional_decimal(row.get("green_score"), "green_score", row_number),
                liveability_score=PropertyImportService._optional_decimal(row.get("liveability_score"), "liveability_score", row_number),
                nearest_metro=PropertyImportService._text(row.get("nearest_metro")),
                nearest_hospital=PropertyImportService._text(row.get("nearest_hospital")),
                nearest_school=PropertyImportService._text(row.get("nearest_school")),
                ai_summary=PropertyImportService._text(row.get("ai_summary")),
                updated_at=now,
            )
        except (InvalidOperation, ValueError) as error:
            raise PropertyImportError(f"Invalid data at CSV row {row_number}: {error}") from error

    @staticmethod
    def _text(value: str | None) -> str | None:
        """Convert an optional CSV cell to stripped text or None."""
        stripped = (value or "").strip()
        return stripped or None

    @classmethod
    def _required_text(cls, row: dict[str, str], field: str, row_number: int) -> str:
        value = cls._text(row.get(field))
        if value is None:
            raise ValueError(f"{field} is required at row {row_number}")
        return value

    @classmethod
    def _decimal(cls, value: str | None, field: str, row_number: int) -> Decimal:
        normalized = cls._text(value)
        if normalized is None:
            raise ValueError(f"{field} is required at row {row_number}")
        result = Decimal(normalized)
        if not result.is_finite():
            raise ValueError(f"{field} must be finite at row {row_number}")
        return result

    @classmethod
    def _optional_decimal(cls, value: str | None, field: str, row_number: int) -> Decimal | None:
        return None if cls._text(value) is None else cls._decimal(value, field, row_number)

    @classmethod
    def _integer(cls, value: str | None, field: str, row_number: int) -> int:
        decimal_value = cls._decimal(value, field, row_number)
        if decimal_value != decimal_value.to_integral_value():
            raise ValueError(f"{field} must be a whole number at row {row_number}")
        return int(decimal_value)

    @classmethod
    def _optional_integer(cls, value: str | None, field: str, row_number: int) -> int | None:
        return None if cls._text(value) is None else cls._integer(value, field, row_number)
