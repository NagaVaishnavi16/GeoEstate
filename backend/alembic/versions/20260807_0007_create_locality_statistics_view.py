"""Create the current PostgreSQL/PostGIS locality analytics view.

Revision ID: 20260807_0007
Revises: 20260801_0006
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260807_0007"
down_revision: Union[str, Sequence[str], None] = "20260801_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create a live view so locality intelligence never needs a refresh job."""
    op.execute(
        """
        CREATE VIEW locality_statistics AS
        SELECT
            p.location AS locality,
            COUNT(*)::bigint AS total_listings,
            ROUND(AVG(p.price_lakh), 2) AS average_price_lakh,
            ROUND((PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY p.price_lakh))::numeric, 2) AS median_price_lakh,
            MIN(p.price_lakh) AS minimum_price_lakh,
            MAX(p.price_lakh) AS maximum_price_lakh,
            ROUND(AVG(p.area_sqft)::numeric, 2) AS average_built_up_area_sqft,
            ROUND(AVG(p.rate_per_sqft) FILTER (WHERE p.rate_per_sqft IS NOT NULL), 2) AS average_price_per_sqft,
            ROUND(ST_Y(ST_Centroid(ST_Collect(p.geometry) FILTER (WHERE p.geometry IS NOT NULL)))::numeric, 6) AS centroid_latitude,
            ROUND(ST_X(ST_Centroid(ST_Collect(p.geometry) FILTER (WHERE p.geometry IS NOT NULL)))::numeric, 6) AS centroid_longitude,
            COUNT(*) FILTER (WHERE p.nearest_metro IS NOT NULL)::bigint AS metro_available_listings,
            COUNT(*) FILTER (WHERE p.nearest_hospital IS NOT NULL)::bigint AS hospital_available_listings,
            COUNT(*) FILTER (WHERE p.nearest_school IS NOT NULL)::bigint AS school_available_listings,
            COUNT(*) FILTER (WHERE p.nearest_park IS NOT NULL)::bigint AS park_available_listings,
            ROUND(AVG(p.nearest_metro_distance_m) FILTER (WHERE p.nearest_metro_distance_m IS NOT NULL), 2) AS average_metro_distance_m,
            ROUND(AVG(p.nearest_hospital_distance_m) FILTER (WHERE p.nearest_hospital_distance_m IS NOT NULL), 2) AS average_hospital_distance_m,
            ROUND(AVG(p.nearest_school_distance_m) FILTER (WHERE p.nearest_school_distance_m IS NOT NULL), 2) AS average_school_distance_m,
            ROUND(AVG(p.nearest_park_distance_m) FILTER (WHERE p.nearest_park_distance_m IS NOT NULL), 2) AS average_park_distance_m,
            ROUND(AVG(p.nearby_park_count) FILTER (WHERE p.nearby_park_count IS NOT NULL), 2) AS average_nearby_park_count,
            ROUND(AVG(p.investment_score) FILTER (WHERE p.investment_score IS NOT NULL), 2) AS average_investment_score,
            ROUND(AVG(p.connectivity_score) FILTER (WHERE p.connectivity_score IS NOT NULL), 2) AS average_connectivity_score,
            ROUND(AVG(p.green_score) FILTER (WHERE p.green_score IS NOT NULL), 2) AS average_green_score,
            ROUND(AVG(p.liveability_score) FILTER (WHERE p.liveability_score IS NOT NULL), 2) AS average_liveability_score
        FROM properties AS p
        GROUP BY p.location;
        """
    )


def downgrade() -> None:
    """Remove the read-only locality analytics view."""
    op.execute("DROP VIEW locality_statistics")
