"""Framework-independent contracts for the reusable property search service."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PropertySortField(StrEnum):
    """Whitelisted property columns that may be used for result ordering."""

    PRICE = "price"
    AREA = "area"
    BEDROOMS = "bedrooms"
    LOCATION = "location"


class SortOrder(StrEnum):
    """Supported ordering directions for property search results."""

    ASC = "asc"
    DESC = "desc"


@dataclass(frozen=True)
class PropertySearchCriteria:
    """Transport-neutral search criteria usable by HTTP and future AI callers."""

    location: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    bedrooms: int | None = None
    min_area: int | None = None
    max_area: int | None = None
    property_type: str | None = None
    building_status: str | None = None
    near_metro: bool = False
    near_hospital: bool = False
    near_school: bool = False
    near_park: bool = False
    limit: int = 20
    offset: int = 0
    sort_by: PropertySortField = PropertySortField.PRICE
    sort_order: SortOrder = SortOrder.ASC
