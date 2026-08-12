# GeoEstate Frontend

React/Vite interface for the existing GeoEstate natural-language property search API. It never contains Gemini, database, or backend credentials.

## Local setup

Create `frontend/.env` from `.env.example` and set the deployed or local FastAPI base URL:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Start the backend with its normal command, then install and start the frontend:

```powershell
cd frontend
pnpm install
pnpm dev
```

The Vite app runs at `http://localhost:5173`. The FastAPI environment must allow that origin through `FRONTEND_CORS_ORIGINS`; the backend default includes `http://localhost:5173` and `http://127.0.0.1:5173`.

## Integration

The only frontend API call is `POST /api/v1/search/natural`. A completed response supplies cards and map markers directly from `results`, including coordinates, nearby-place data, and deterministic score fields. Leaflet uses OpenStreetMap tiles; no Google Maps or Places API is used.
