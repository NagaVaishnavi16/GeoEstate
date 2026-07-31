"""Small framework-independent utilities reserved for shared helpers."""

from .geospatial import (
    Coordinate,
    CoordinateValidationError,
    normalize_locality,
    validate_hyderabad_coordinate,
    validate_telangana_coordinate,
)

__all__ = [
    "Coordinate",
    "CoordinateValidationError",
    "normalize_locality",
    "validate_hyderabad_coordinate",
    "validate_telangana_coordinate",
]
