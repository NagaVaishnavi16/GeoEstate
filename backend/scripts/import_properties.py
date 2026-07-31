"""Import property listings from CSV into PostgreSQL."""

import asyncio
import csv
import sys
from decimal import Decimal
from pathlib import Path

# Allow importing from app/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.db.session import AsyncSessionFactory
from app.models.property import Property


CSV_PATH = PROJECT_ROOT / "outputs" / "processed_hyderabad_properties.csv"


def to_decimal(value):
    if value is None or value == "":
        return None
    return Decimal(value)


def to_int(value):
    if value is None or value == "":
        return None
    return int(value)


async def main():
    if not CSV_PATH.exists():
        print(f"CSV not found: {CSV_PATH}")
        return

    async with AsyncSessionFactory() as session:

        inserted = 0
        skipped = 0

        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:

                existing = await session.get(Property, row["property_id"])
                if existing:
                    skipped += 1
                    continue

                property_obj = Property(
                    property_id=row["property_id"],
                    title=row["title"] or "",
                    location=row["location"],
                    price_lakh=to_decimal(row["price_lakh"]),
                    rate_per_sqft=to_decimal(row["rate_per_sqft"]),
                    area_sqft=int(row["area_sqft"]),
                    building_status=row["building_status"] or "",
                    bedrooms=to_int(row["bedrooms"]),
                    latitude=to_decimal(row["latitude"]),
                    longitude=to_decimal(row["longitude"]),
                    investment_score=to_decimal(row["investment_score"]),
                    connectivity_score=to_decimal(row["connectivity_score"]),
                    green_score=to_decimal(row["green_score"]),
                    liveability_score=to_decimal(row["liveability_score"]),
                    nearest_metro=row["nearest_metro"] or None,
                    nearest_hospital=row["nearest_hospital"] or None,
                    nearest_school=row["nearest_school"] or None,
                    ai_summary=row["ai_summary"] or None,
                )

                session.add(property_obj)
                inserted += 1

        await session.commit()

    print("=" * 50)
    print(f"Imported : {inserted}")
    print(f"Skipped  : {skipped}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())