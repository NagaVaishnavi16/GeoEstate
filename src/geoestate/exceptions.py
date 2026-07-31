"""Exceptions specific to the GeoEstate data layer."""


class SchemaError(ValueError):
    """Raised when an input file cannot be mapped to the required schema."""
