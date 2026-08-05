"""Durable Overpass cache for coordinate-bucket nearby-place queries."""

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NearbyPlaceCache(Base):
    """Store one resolved Overpass category result per rounded coordinate bucket."""

    __tablename__ = "nearby_place_cache"
    __table_args__ = (
        CheckConstraint("category IN ('metro', 'hospital', 'school', 'park')", name="ck_nearby_place_cache_category"),
        CheckConstraint("status IN ('success', 'not_found', 'failed')", name="ck_nearby_place_cache_status"),
    )

    coordinate_bucket: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str] = mapped_column(String(20), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    queried_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
