"""Deterministic, data-backed property intelligence scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping


ZERO = Decimal("0")
ONE_HUNDRED = Decimal("100")
SCORE_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class PropertyScoringConfig:
    """Named scoring inputs kept separate from orchestration and persistence."""

    metro_weight: Decimal = Decimal("0.40")
    hospital_weight: Decimal = Decimal("0.30")
    school_weight: Decimal = Decimal("0.30")
    metro_decay_m: Decimal = Decimal("1500")
    hospital_decay_m: Decimal = Decimal("3000")
    school_decay_m: Decimal = Decimal("2500")
    connectivity_cutoff_m: int = 10_000

    park_distance_weight: Decimal = Decimal("0.50")
    park_count_weight: Decimal = Decimal("0.50")
    park_decay_m: Decimal = Decimal("1500")
    park_distance_cutoff_m: int = 10_000
    park_count_cap: int = 5

    investment_rate_weight: Decimal = Decimal("0.50")
    investment_status_weight: Decimal = Decimal("0.30")
    investment_area_weight: Decimal = Decimal("0.20")
    building_status_scores: Mapping[str, Decimal] = field(
        default_factory=lambda: {
            "ready to move": Decimal("100"),
            "new": Decimal("85"),
            "resale": Decimal("75"),
            "under construction": Decimal("60"),
        }
    )

    liveability_connectivity_weight: Decimal = Decimal("0.40")
    liveability_green_weight: Decimal = Decimal("0.30")
    liveability_amenity_weight: Decimal = Decimal("0.30")
    amenity_category_count: int = 4


@dataclass(frozen=True)
class PropertyScoringInput:
    """Verified property facts used by the deterministic scoring formulas."""

    rate_per_sqft: Decimal | None
    area_sqft: int | None
    building_status: str | None
    locality_average_price_per_sqft: Decimal | None
    locality_average_area_sqft: Decimal | None
    nearest_metro_distance_m: int | None
    nearest_hospital_distance_m: int | None
    nearest_school_distance_m: int | None
    nearest_park_distance_m: int | None
    nearby_park_count: int | None
    nearest_metro: str | None = None
    nearest_hospital: str | None = None
    nearest_school: str | None = None
    nearest_park: str | None = None


@dataclass(frozen=True)
class PropertyScores:
    """Nullable, independently useful scores that satisfy database constraints."""

    connectivity_score: Decimal | None
    green_score: Decimal | None
    investment_score: Decimal | None
    liveability_score: Decimal | None


class PropertyScoringService:
    """Calculate explainable scores without database, HTTP, or framework dependencies."""

    def __init__(self, config: PropertyScoringConfig | None = None) -> None:
        self._config = config or PropertyScoringConfig()

    def score(self, property_data: PropertyScoringInput) -> PropertyScores:
        """Calculate all indicators from supplied verified property and locality facts."""
        connectivity = self.connectivity_score(property_data)
        green = self.green_score(property_data)
        investment = self.investment_score(property_data)
        liveability = self.liveability_score(property_data, connectivity=connectivity, green=green)
        return PropertyScores(connectivity, green, investment, liveability)

    def connectivity_score(self, property_data: PropertyScoringInput) -> Decimal | None:
        """Weight available metro, hospital, and school distance-decay contributions."""
        config = self._config
        components = (
            (property_data.nearest_metro_distance_m, config.metro_weight, config.metro_decay_m),
            (property_data.nearest_hospital_distance_m, config.hospital_weight, config.hospital_decay_m),
            (property_data.nearest_school_distance_m, config.school_weight, config.school_decay_m),
        )
        available = [
            (weight, self._distance_decay(distance, decay, config.connectivity_cutoff_m))
            for distance, weight, decay in components
            if distance is not None
        ]
        return self._weighted_available_score(available)

    def green_score(self, property_data: PropertyScoringInput) -> Decimal | None:
        """Combine a park-distance decay with capped, diminishing park-count evidence."""
        config = self._config
        available: list[tuple[Decimal, Decimal]] = []
        if property_data.nearest_park_distance_m is not None:
            available.append(
                (
                    config.park_distance_weight,
                    self._distance_decay(
                        property_data.nearest_park_distance_m,
                        config.park_decay_m,
                        config.park_distance_cutoff_m,
                    ),
                )
            )
        if property_data.nearby_park_count is not None:
            capped_count = min(max(property_data.nearby_park_count, 0), config.park_count_cap)
            available.append(
                (config.park_count_weight, ONE_HUNDRED * Decimal(capped_count) / Decimal(config.park_count_cap))
            )
        return self._weighted_available_score(available)

    def investment_score(self, property_data: PropertyScoringInput) -> Decimal | None:
        """Calculate a comparative value indicator; never infer a missing locality benchmark."""
        benchmark = property_data.locality_average_price_per_sqft
        rate = property_data.rate_per_sqft
        if benchmark is None or benchmark <= ZERO or rate is None or rate <= ZERO:
            return None

        config = self._config
        available: list[tuple[Decimal, Decimal]] = [
            (config.investment_rate_weight, self._clamp(ONE_HUNDRED * benchmark / rate))
        ]
        status_score = config.building_status_scores.get((property_data.building_status or "").casefold())
        if status_score is not None:
            available.append((config.investment_status_weight, status_score))
        average_area = property_data.locality_average_area_sqft
        if property_data.area_sqft is not None and property_data.area_sqft > 0 and average_area is not None and average_area > ZERO:
            available.append(
                (config.investment_area_weight, self._clamp(ONE_HUNDRED * Decimal(property_data.area_sqft) / average_area))
            )
        return self._weighted_available_score(available)

    def liveability_score(
        self,
        property_data: PropertyScoringInput,
        *,
        connectivity: Decimal | None,
        green: Decimal | None,
    ) -> Decimal | None:
        """Combine available connectivity, green, and verified amenity-availability evidence."""
        config = self._config
        available: list[tuple[Decimal, Decimal]] = []
        if connectivity is not None:
            available.append((config.liveability_connectivity_weight, connectivity))
        if green is not None:
            available.append((config.liveability_green_weight, green))
        amenity_score = self._amenity_availability_score(property_data)
        if amenity_score is not None:
            available.append((config.liveability_amenity_weight, amenity_score))
        return self._weighted_available_score(available)

    def _amenity_availability_score(self, property_data: PropertyScoringInput) -> Decimal | None:
        """Score only verified nearby-place names; no verified amenities means insufficient data."""
        available_count = sum(
            value is not None
            for value in (
                property_data.nearest_metro,
                property_data.nearest_hospital,
                property_data.nearest_school,
                property_data.nearest_park,
            )
        )
        if available_count == 0:
            return None
        return ONE_HUNDRED * Decimal(available_count) / Decimal(self._config.amenity_category_count)

    @staticmethod
    def _distance_decay(distance_m: int, decay_m: Decimal, cutoff_m: int) -> Decimal:
        """Return a bounded exponential distance score, with no score past the category cutoff."""
        if distance_m < 0 or distance_m >= cutoff_m:
            return ZERO
        return ONE_HUNDRED * (-(Decimal(distance_m) / decay_m)).exp()

    @staticmethod
    def _weighted_available_score(components: list[tuple[Decimal, Decimal]]) -> Decimal | None:
        """Redistribute only across known factors instead of treating missing facts as zero."""
        if not components:
            return None
        total_weight = sum(weight for weight, _ in components)
        score = sum(weight * value for weight, value in components) / total_weight
        return PropertyScoringService._round(PropertyScoringService._clamp(score))

    @staticmethod
    def _clamp(value: Decimal) -> Decimal:
        """Constrain numerical output to the property-table score contract."""
        return max(ZERO, min(ONE_HUNDRED, value))

    @staticmethod
    def _round(value: Decimal) -> Decimal:
        """Use stable two-decimal rounding compatible with NUMERIC(5, 2)."""
        return value.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)
