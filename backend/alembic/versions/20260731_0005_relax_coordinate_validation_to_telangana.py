"""Relax coordinate constraints from Hyderabad to Telangana.

Revision ID: 20260731_0005
Revises: 20260730_0004
Create Date: 2026-07-31
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260731_0005"
down_revision: Union[str, Sequence[str], None] = "20260730_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow valid Telangana localities while retaining coordinate guardrails."""
    op.drop_constraint("ck_properties_hyderabad_latitude", "properties", type_="check")
    op.drop_constraint("ck_properties_hyderabad_longitude", "properties", type_="check")
    op.drop_constraint("ck_geocode_cache_hyderabad_latitude", "geocode_cache", type_="check")
    op.drop_constraint("ck_geocode_cache_hyderabad_longitude", "geocode_cache", type_="check")
    op.create_check_constraint("ck_properties_telangana_latitude", "properties", "latitude IS NULL OR latitude BETWEEN 15.8 AND 19.9")
    op.create_check_constraint("ck_properties_telangana_longitude", "properties", "longitude IS NULL OR longitude BETWEEN 77.0 AND 81.3")
    op.create_check_constraint("ck_geocode_cache_telangana_latitude", "geocode_cache", "latitude IS NULL OR latitude BETWEEN 15.8 AND 19.9")
    op.create_check_constraint("ck_geocode_cache_telangana_longitude", "geocode_cache", "longitude IS NULL OR longitude BETWEEN 77.0 AND 81.3")


def downgrade() -> None:
    """Restore the prior Hyderabad-focused coordinate validation bounds."""
    op.drop_constraint("ck_properties_telangana_latitude", "properties", type_="check")
    op.drop_constraint("ck_properties_telangana_longitude", "properties", type_="check")
    op.drop_constraint("ck_geocode_cache_telangana_latitude", "geocode_cache", type_="check")
    op.drop_constraint("ck_geocode_cache_telangana_longitude", "geocode_cache", type_="check")
    op.create_check_constraint("ck_properties_hyderabad_latitude", "properties", "latitude IS NULL OR latitude BETWEEN 16.0 AND 19.0")
    op.create_check_constraint("ck_properties_hyderabad_longitude", "properties", "longitude IS NULL OR longitude BETWEEN 77.0 AND 80.5")
    op.create_check_constraint("ck_geocode_cache_hyderabad_latitude", "geocode_cache", "latitude IS NULL OR latitude BETWEEN 16.0 AND 19.0")
    op.create_check_constraint("ck_geocode_cache_hyderabad_longitude", "geocode_cache", "longitude IS NULL OR longitude BETWEEN 77.0 AND 80.5")
