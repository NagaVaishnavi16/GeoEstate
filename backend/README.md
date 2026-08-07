# GeoEstate Intelligence API

This is the runnable backend for GeoEstate Intelligence. It uses FastAPI, asynchronous SQLAlchemy 2.0, PostgreSQL/PostGIS, Alembic, Pydantic v2, and Uvicorn. It exposes public read and search endpoints; authentication, user accounts, frontend work, maps, satellite imagery, and recommendation engines remain outside the current scope.

## Architecture

- `app/main.py` creates the FastAPI application, lifecycle hooks, request logging, and Swagger/OpenAPI routes.
- `app/api/` is the HTTP boundary: route definitions and dependency providers only.
- `app/core/` contains environment settings and process-wide logging.
- `app/db/` provides the declarative base, async engine, and request-scoped session dependency.
- `app/models/` holds SQLAlchemy database models.
- `app/schemas/` holds Pydantic v2 API input/output contracts.
- `app/repositories/` owns SQLAlchemy query and CRUD operations.
- `app/services/` owns domain-facing use cases and keeps repositories out of routes.
- `app/utils/` is reserved for framework-independent shared helpers.
- `alembic/` contains async migration configuration and the initial schema migration.

## Enrichment pipeline — Milestone 1

`scripts/enrich_geocodes.py` is the single production enrichment entry point. Milestone 1 implements two resumable PostgreSQL stages:

- `geocode`: selects only properties with a missing latitude or longitude, resolves unique localities through `geocode_cache` and Nominatim, and fills only null coordinate components.
- `geometry`: selects only coordinate-complete properties whose PostGIS geometry is null, then safely regenerates only those missing points.

Each stage uses 100-property cursor batches by default, commits every batch, and logs progress at 50-property intervals. Re-running a stage is safe: completed properties are excluded, valid coordinates are not overwritten, and cached failed/successful localities are never sent to Nominatim again.

Every failed Nominatim lookup now logs its locality, HTTP status, raw result count, selected coordinates, validation result, and classified `failure_reason`. Cache failures are persisted as one of `empty_response`, `coordinate_validation_failed`, `parser_failed`, `timeout`, or `http_error`. Database-write failures are logged distinctly because an unavailable database cannot persist its own failure record. Legacy failed cache rows without a `failure_reason` are reclassified once; use `--retry-failed-cache` only for an explicit operator-approved retry of already-classified failures.

Before running it, configure an identifying `GEOCODING_USER_AGENT` and contact email in `.env`. The client intentionally waits at least one second between provider requests. `GEOCODING_LOCALITY_ALIASES` is an environment-configurable JSON object for spelling variants and aliases. Each lookup prefers a Hyderabad query, then tries the configured canonical locality and progressively broader Telangana and India queries. Valid Telangana coordinates are accepted, while coordinates outside Telangana remain rejected. The command logs a final coverage summary containing total properties, geocoded properties, remaining properties, and the highest-impact classified failures.

```powershell
cd backend
alembic upgrade head
python scripts/enrich_geocodes.py
```

Use `--stage geocode` or `--stage geometry` to run one stage; use `--batch-size 100` to override the configured batch size. `ENRICHMENT_BATCH_SIZE` and `ENRICHMENT_PROGRESS_INTERVAL` are configured in `.env`.

Coordinates are validated at three layers: six-decimal numeric parsing, Telangana geographic bounds in the geocoding utility, and PostgreSQL check constraints. `latitude` and `longitude` already belong to every `PropertyResponse`, so they are automatically returned by both property endpoints once populated.

## Phase 3 geospatial search

Phase 3 adds the PostGIS extension, `geometry(Point, 4326)` to every property, a GiST spatial index, and a PostgreSQL trigger that keeps geometry synchronized whenever latitude or longitude changes. Existing coordinate-enriched properties are backfilled during the migration.

The dedicated `PropertySearchService` receives a transport-neutral `PropertySearchCriteria` contract. `POST /search` is only an HTTP adapter; future frontend and AI callers must use that same service. It supports case-insensitive locality matching, INR `min_price`/`max_price` filtering (the stored `price_lakh` is converted internally), bedrooms, area bounds, pagination, and safe whitelisted sorting.

## Stage 4 locality intelligence

Migration `20260807_0007_create_locality_statistics_view.py` creates a live PostgreSQL/PostGIS `locality_statistics` view. It calculates listing counts, average/median/minimum/maximum price, average area, average rate per square foot, and PostGIS centroids using SQL aggregation only. It also exposes locality-level availability counts for existing nearby-place enrichment and averages of any populated enrichment scores.

After `alembic upgrade head`, use `GET /api/v1/localities`, `GET /api/v1/localities/{locality}`, `GET /api/v1/localities/top-expensive`, or `GET /api/v1/localities/most-affordable`. The view is intentionally live rather than materialized, so no refresh job is required when property data changes.

## Stage 5 natural-language property search

Set `GEMINI_API_KEY` and optionally `GEMINI_MODEL=gemini-2.5-flash` in `backend/.env`. `POST /api/v1/search/natural` sends the query to Gemini only for JSON-schema-constrained filter extraction, validates that output with Pydantic, and then delegates to the existing `PropertySearchService`. Gemini never receives database access, SQL, or result-ranking responsibility.

The request path remains deliberately narrow: API route → `NaturalLanguageSearchService` → Gemini intent parser → Pydantic validation → existing `PropertySearchService` → repository. Invalid, incomplete, or provider-failed intent never reaches the search service. User input is never used to construct SQL.

```json
{
  "query": "Show me 3 BHK apartments under 1 crore in Gachibowli near metro"
}
```

Malformed provider output returns `validation_error` without running a database search. Ambiguous requests return `needs_clarification`; otherwise the response includes the extracted filters, property results, and total result count.

Additional supported query examples:

- `Flats near Raidurg metro below 80 lakh`
- `Ready-to-move villas above 2000 sqft`
- `Affordable apartments in Kukatpally near hospitals`
- `2 BHK properties in Kondapur with nearby schools`

```json
{
  "location": "Gachibowli",
  "min_price": 5000000,
  "max_price": 9000000,
  "bedrooms": 3,
  "limit": 20,
  "offset": 0,
  "sort_by": "price"
}
```

`GET /properties/{property_id}/details` returns the property, explicit coordinates, and a stable `future_intelligence` extension object. `GET /health` now checks PostgreSQL and PostGIS separately and returns `status`, `database`, `postgis`, and `version`.

Run `alembic upgrade head` after adding the `GeoAlchemy2` dependency. The Phase 3 schema remains limited to the canonical dataset plus computed PostGIS geometry; resale and amenity fields are intentionally deferred until a verified source supplies them.

## Enrichment pipeline — Stage 3 nearby places

The same `scripts/enrich_geocodes.py` entry point now includes the `nearby` stage. It processes only coordinate-complete properties with at least one missing nearby-place field. For each rounded coordinate bucket, `NearbyPlaceService` checks PostgreSQL cache rows before making a rate-limited, bounded-retry Overpass query for metro stations, hospitals, schools, and parks. The nearest named feature and its WGS84 Haversine distance are stored; parks also receive a count inside the configured park-density radius. Guarded repository updates fill only null columns.

```powershell
cd backend
alembic upgrade head
python -m scripts.enrich_geocodes --stage nearby
```

`OVERPASS_*` settings in `.env` configure endpoint, throttling, timeout, retry/backoff, search radius, and park-count radius. The stage runs in 100-record transactions by default, commits each batch, and logs progress every 50 records. A stopped run resumes safely because committed rows are skipped and the durable cache prevents duplicate requests for already-resolved coordinate/category pairs.

## Setup

From the repository root, install the declared dependencies. Then copy `.env.example` to `.env` inside `backend/` and set `DATABASE_URL` for PostgreSQL.

```powershell
cd backend
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`; automatic Swagger documentation is at `/docs` and the OpenAPI document is at `/openapi.json`.

## Endpoints

- `POST /search` runs the reusable structured property search.
- `POST /api/v1/search/natural` extracts validated filters, then delegates to the structured search service.
- `GET /api/v1/localities` returns locality-level statistics from the live PostgreSQL/PostGIS view.
- `GET /api/v1/localities/{locality}` returns a single locality's statistics.
- `GET /api/v1/localities/top-expensive` and `GET /api/v1/localities/most-affordable` return price-ranked locality pages.

- `GET /health` — verifies that the API can query PostgreSQL.
- `GET /properties?limit=50&offset=0` — returns an ordered, offset-paginated listing.
- `GET /properties/{property_id}` — returns one listing, for example `hyd-4a68c6c277a56b1997f7`.

The `properties` model matches all 18 fields in `outputs/processed_hyderabad_properties.csv`; its enrichment fields remain nullable until authoritative geospatial or AI jobs populate them.

## Django replacement note

The old Django source is not referenced by this FastAPI runtime and Django dependencies have been removed. It remains in the workspace only because the managed environment denied deletion of existing files.
