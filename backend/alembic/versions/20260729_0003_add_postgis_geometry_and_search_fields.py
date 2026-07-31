"""Enable PostGIS and add geometry-backed property search support.

Revision ID: 20260729_0003
Revises: 20260729_0002
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260729_0003"
down_revision: Union[str, Sequence[str], None] = "20260729_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Install PostGIS, add geometry support, and backfill point values."""
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("ALTER TABLE properties ADD COLUMN geometry geometry(POINT, 4326)")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION geoestate_sync_property_geometry()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.latitude IS NULL OR NEW.longitude IS NULL THEN
                NEW.geometry := NULL;
            ELSE
                NEW.geometry := ST_SetSRID(ST_MakePoint(NEW.longitude::double precision, NEW.latitude::double precision), 4326);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER properties_sync_geometry
        BEFORE INSERT OR UPDATE OF latitude, longitude ON properties
        FOR EACH ROW EXECUTE FUNCTION geoestate_sync_property_geometry();
        """
    )
    op.execute(
        """
        UPDATE properties
        SET geometry = ST_SetSRID(ST_MakePoint(longitude::double precision, latitude::double precision), 4326)
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
        """
    )
    op.create_index("properties_geometry_gix", "properties", ["geometry"], postgresql_using="gist")


def downgrade() -> None:
    """Remove PostGIS-backed fields without disabling the shared extension."""
    op.drop_index("properties_geometry_gix", table_name="properties")
    op.execute("DROP TRIGGER IF EXISTS properties_sync_geometry ON properties")
    op.execute("DROP FUNCTION IF EXISTS geoestate_sync_property_geometry()")
    op.execute("ALTER TABLE properties DROP COLUMN geometry")
