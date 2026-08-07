"""Read-only SQLAlchemy mapping for the PostgreSQL locality analytics view."""

from decimal import Decimal

from sqlalchemy import BigInteger, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LocalityStatistics(Base):
    """One current, database-computed analytics record per property locality."""

    __tablename__ = "locality_statistics"
    __table_args__ = {"info": {"is_view": True}}

    locality: Mapped[str] = mapped_column(primary_key=True)
    total_listings: Mapped[int] = mapped_column(BigInteger)
    average_price_lakh: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    median_price_lakh: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    minimum_price_lakh: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    maximum_price_lakh: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    average_built_up_area_sqft: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    average_price_per_sqft: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    centroid_latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    centroid_longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    metro_available_listings: Mapped[int] = mapped_column(BigInteger)
    hospital_available_listings: Mapped[int] = mapped_column(BigInteger)
    school_available_listings: Mapped[int] = mapped_column(BigInteger)
    park_available_listings: Mapped[int] = mapped_column(BigInteger)
    average_metro_distance_m: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    average_hospital_distance_m: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    average_school_distance_m: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    average_park_distance_m: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    average_nearby_park_count: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    average_investment_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    average_connectivity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    average_green_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    average_liveability_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
