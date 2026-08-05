"""Add nearby-place enrichment fields and durable Overpass cache.

Revision ID: 20260801_0006
Revises: 20260731_0005
Create Date: 2026-08-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260801_0006"
down_revision: Union[str, Sequence[str], None] = "20260731_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add only nullable computed nearby-place attributes and their provider cache."""
    for name, column in (
        ("nearest_park", sa.Column("nearest_park", sa.String(length=255), nullable=True)),
        ("nearest_metro_distance_m", sa.Column("nearest_metro_distance_m", sa.Integer(), nullable=True)),
        ("nearest_hospital_distance_m", sa.Column("nearest_hospital_distance_m", sa.Integer(), nullable=True)),
        ("nearest_school_distance_m", sa.Column("nearest_school_distance_m", sa.Integer(), nullable=True)),
        ("nearest_park_distance_m", sa.Column("nearest_park_distance_m", sa.Integer(), nullable=True)),
        ("nearby_park_count", sa.Column("nearby_park_count", sa.Integer(), nullable=True)),
    ):
        op.add_column("properties", column)
    op.create_check_constraint("ck_properties_nearby_park_count", "properties", "nearby_park_count IS NULL OR nearby_park_count >= 0")
    op.create_check_constraint("ck_properties_nearest_metro_distance_m", "properties", "nearest_metro_distance_m IS NULL OR nearest_metro_distance_m >= 0")
    op.create_check_constraint("ck_properties_nearest_hospital_distance_m", "properties", "nearest_hospital_distance_m IS NULL OR nearest_hospital_distance_m >= 0")
    op.create_check_constraint("ck_properties_nearest_school_distance_m", "properties", "nearest_school_distance_m IS NULL OR nearest_school_distance_m >= 0")
    op.create_check_constraint("ck_properties_nearest_park_distance_m", "properties", "nearest_park_distance_m IS NULL OR nearest_park_distance_m >= 0")
    op.create_table(
        "nearby_place_cache",
        sa.Column("coordinate_bucket", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("queried_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("category IN ('metro', 'hospital', 'school', 'park')", name="ck_nearby_place_cache_category"),
        sa.CheckConstraint("status IN ('success', 'not_found', 'failed')", name="ck_nearby_place_cache_status"),
        sa.PrimaryKeyConstraint("coordinate_bucket", "category"),
    )


def downgrade() -> None:
    """Remove Stage 3 cache and fields in reverse dependency order."""
    op.drop_table("nearby_place_cache")
    for name in (
        "ck_properties_nearest_park_distance_m",
        "ck_properties_nearest_school_distance_m",
        "ck_properties_nearest_hospital_distance_m",
        "ck_properties_nearest_metro_distance_m",
        "ck_properties_nearby_park_count",
    ):
        op.drop_constraint(name, "properties", type_="check")
    for name in (
        "nearby_park_count",
        "nearest_park_distance_m",
        "nearest_school_distance_m",
        "nearest_hospital_distance_m",
        "nearest_metro_distance_m",
        "nearest_park",
    ):
        op.drop_column("properties", name)
