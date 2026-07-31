"""SQLAlchemy model for canonical GeoEstate property listings."""

from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Property(Base):
    """A cleaned listing with empty fields reserved for future enrichment."""

    __tablename__ = "properties"
    __table_args__ = (
        CheckConstraint("investment_score IS NULL OR investment_score BETWEEN 0 AND 100", name="ck_properties_investment_score"),
        CheckConstraint("connectivity_score IS NULL OR connectivity_score BETWEEN 0 AND 100", name="ck_properties_connectivity_score"),
        CheckConstraint("green_score IS NULL OR green_score BETWEEN 0 AND 100", name="ck_properties_green_score"),
        CheckConstraint("liveability_score IS NULL OR liveability_score BETWEEN 0 AND 100", name="ck_properties_liveability_score"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN 15.8 AND 19.9", name="ck_properties_telangana_latitude"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN 77.0 AND 81.3", name="ck_properties_telangana_longitude"),
        Index("property_location_price_idx", "location", "price_lakh"),
    )

    property_id: Mapped[str] = mapped_column(String(24), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    price_lakh: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    rate_per_sqft: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    area_sqft: Mapped[int] = mapped_column(Integer, nullable=False)
    building_status: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    bedrooms: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    investment_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    connectivity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    green_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    liveability_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    nearest_metro: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nearest_hospital: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nearest_school: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    geometry: Mapped[object | None] = mapped_column(Geometry(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
