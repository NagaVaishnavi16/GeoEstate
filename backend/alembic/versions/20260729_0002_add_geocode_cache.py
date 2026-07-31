"""Add locality geocoding cache and Hyderabad coordinate constraints.

Revision ID: 20260729_0002
Revises: 20260729_0001
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0002"
down_revision: Union[str, Sequence[str], None] = "20260729_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create durable locality cache storage and enforce coordinate bounds."""
    op.create_table(
        "geocode_cache",
        sa.Column("location_key", sa.String(length=255), nullable=False),
        sa.Column("locality", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("queried_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('success', 'not_found', 'failed')", name="ck_geocode_cache_status"),
        sa.CheckConstraint("latitude IS NULL OR latitude BETWEEN 16.0 AND 19.0", name="ck_geocode_cache_hyderabad_latitude"),
        sa.CheckConstraint("longitude IS NULL OR longitude BETWEEN 77.0 AND 80.5", name="ck_geocode_cache_hyderabad_longitude"),
        sa.PrimaryKeyConstraint("location_key"),
    )
    op.create_check_constraint(
        "ck_properties_hyderabad_latitude",
        "properties",
        "latitude IS NULL OR latitude BETWEEN 16.0 AND 19.0",
    )
    op.create_check_constraint(
        "ck_properties_hyderabad_longitude",
        "properties",
        "longitude IS NULL OR longitude BETWEEN 77.0 AND 80.5",
    )


def downgrade() -> None:
    """Remove Phase 2 cache and coordinate-range constraints."""
    op.drop_constraint("ck_properties_hyderabad_longitude", "properties", type_="check")
    op.drop_constraint("ck_properties_hyderabad_latitude", "properties", type_="check")
    op.drop_table("geocode_cache")
