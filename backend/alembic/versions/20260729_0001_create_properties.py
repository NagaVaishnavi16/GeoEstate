"""Create the canonical properties table.

Revision ID: 20260729_0001
Revises:
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the Phase 1 property table and indexes."""
    op.create_table(
        "properties",
        sa.Column("property_id", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=255), nullable=False),
        sa.Column("price_lakh", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("rate_per_sqft", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("area_sqft", sa.Integer(), nullable=False),
        sa.Column("building_status", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("bedrooms", sa.SmallInteger(), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("investment_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("connectivity_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("green_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("liveability_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("nearest_metro", sa.String(length=255), nullable=True),
        sa.Column("nearest_hospital", sa.String(length=255), nullable=True),
        sa.Column("nearest_school", sa.String(length=255), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("investment_score IS NULL OR investment_score BETWEEN 0 AND 100", name="ck_properties_investment_score"),
        sa.CheckConstraint("connectivity_score IS NULL OR connectivity_score BETWEEN 0 AND 100", name="ck_properties_connectivity_score"),
        sa.CheckConstraint("green_score IS NULL OR green_score BETWEEN 0 AND 100", name="ck_properties_green_score"),
        sa.CheckConstraint("liveability_score IS NULL OR liveability_score BETWEEN 0 AND 100", name="ck_properties_liveability_score"),
        sa.PrimaryKeyConstraint("property_id"),
    )
    op.create_index("ix_properties_location", "properties", ["location"])
    op.create_index("property_location_price_idx", "properties", ["location", "price_lakh"])


def downgrade() -> None:
    """Remove the Phase 1 properties table."""
    op.drop_index("property_location_price_idx", table_name="properties")
    op.drop_index("ix_properties_location", table_name="properties")
    op.drop_table("properties")
