"""Persist classified geocoding failure reasons.

Revision ID: 20260730_0004
Revises: 20260729_0003
Create Date: 2026-07-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260730_0004"
down_revision: Union[str, Sequence[str], None] = "20260729_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a machine-readable reason for each durable failed cache entry."""
    op.add_column("geocode_cache", sa.Column("failure_reason", sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Remove the classified failure-reason column."""
    op.drop_column("geocode_cache", "failure_reason")
