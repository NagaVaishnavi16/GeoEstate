"""Framework-independent locality normalization and coordinate validation."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re

TELANGANA_LATITUDE_MIN = Decimal("15.8")
TELANGANA_LATITUDE_MAX = Decimal("19.9")
TELANGANA_LONGITUDE_MIN = Decimal("77.0")
TELANGANA_LONGITUDE_MAX = Decimal("81.3")


class CoordinateValidationError(ValueError):
    """Raised when an external geocoder returns invalid or out-of-region coordinates."""


@dataclass(frozen=True)
class Coordinate:
    """Validated WGS84 coordinate pair for a Telangana property locality."""

    latitude: Decimal
    longitude: Decimal


def normalize_locality(locality: str) -> str:
    """Create a stable cache key from a user-facing locality name."""
    normalized = re.sub(r"\s+", " ", locality).strip().casefold()
    if not normalized:
        raise ValueError("Locality cannot be blank")
    return normalized


def validate_telangana_coordinate(latitude: str | Decimal, longitude: str | Decimal) -> Coordinate:
    """Validate a finite WGS84 point inside the Telangana geographic extent."""
    try:
        validated_latitude = Decimal(str(latitude)).quantize(Decimal("0.000001"))
        validated_longitude = Decimal(str(longitude)).quantize(Decimal("0.000001"))
    except (InvalidOperation, ValueError) as error:
        raise CoordinateValidationError("Geocoder returned non-numeric coordinates") from error
    if not validated_latitude.is_finite() or not validated_longitude.is_finite():
        raise CoordinateValidationError("Geocoder returned non-finite coordinates")
    if not TELANGANA_LATITUDE_MIN <= validated_latitude <= TELANGANA_LATITUDE_MAX:
        raise CoordinateValidationError("Latitude falls outside the Telangana validation range")
    if not TELANGANA_LONGITUDE_MIN <= validated_longitude <= TELANGANA_LONGITUDE_MAX:
        raise CoordinateValidationError("Longitude falls outside the Telangana validation range")
    return Coordinate(latitude=validated_latitude, longitude=validated_longitude)


def validate_hyderabad_coordinate(latitude: str | Decimal, longitude: str | Decimal) -> Coordinate:
    """Backward-compatible alias for Telangana validation used by older callers."""
    return validate_telangana_coordinate(latitude, longitude)
