# GeoEstate Intelligence — Data Layer

This repository prepares raw Hyderabad property listings for future geospatial enrichment, recommendation models, satellite analytics, and natural-language search. Its runnable backend foundation is FastAPI-based and intentionally contains no authentication, AI logic, or frontend code.

## What it does

- normalizes source headers to `snake_case` and supports common source aliases;
- removes export-index columns, whitespace-only values, invalid core rows, and exact business duplicates;
- cleans text and safely converts price, rate, and area fields to nullable numeric types;
- derives `bedrooms` from listing titles when a dedicated bedroom field is absent;
- creates deterministic, unique `property_id` values;
- adds typed enrichment placeholders without fabricating geospatial or AI values.

## Project layout

```text
src/geoestate/
  cli.py            Command-line entry point
  config.py         Pipeline settings and canonical schema
  cleaning.py       Reusable cleaning and standardization functions
  pipeline.py       Orchestration and CSV I/O
  exceptions.py     Domain exception types
tests/
  test_pipeline.py  Core pipeline test
backend/
  app/              FastAPI clean-architecture application
  alembic/          PostgreSQL schema migrations
  .env.example      Required environment-variable template
```

## Run

Install the package in an environment with Python 3.11+ and pandas, then run:

```powershell
python -m geoestate "C:\path\to\Hyderbad_House_price.csv" --output ".\outputs\processed_hyderabad_properties.csv"
```

The output includes `latitude`, `longitude`, `investment_score`, `connectivity_score`, `green_score`, `liveability_score`, `nearest_metro`, `nearest_hospital`, `nearest_school`, and `ai_summary` as null, typed columns for later enrichment.

`property_id` is a stable SHA-256-based identifier generated from canonical listing content plus its occurrence number. Identical duplicate records are removed before IDs are assigned; remaining repeated listing content still receives distinct IDs.

## Backend setup

See `backend/README.md` for the FastAPI Phase 1 setup, PostgreSQL environment variables, Alembic migration, and public API endpoints.
