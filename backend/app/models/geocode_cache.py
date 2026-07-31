"""Persistent cache for locality-level geocoding lookups."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeocodeCache(Base):
    """Store one durable geocoding outcome per normalized locality and provider."""

    __tablename__ = "geocode_cache"
    __table_args__ = (
        CheckConstraint("status IN ('success', 'not_found', 'failed')", name="ck_geocode_cache_status"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN 15.8 AND 19.9", name="ck_geocode_cache_telangana_latitude"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN 77.0 AND 81.3", name="ck_geocode_cache_telangana_longitude"),
    )

    location_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    locality: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    queried_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
