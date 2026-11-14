# Field Shift Backend Service

FastAPI Python backend providing data analysis, satellite data integration, deterministic rotation scoring, and RESTful API endpoints (1–37) for Field Shift.

---

## 1. Directory Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application, CORS & router registration
│   ├── config.py               # Environment configuration
│   ├── db.py                   # Neon PostgreSQL connection, transactions & schema initialization
│   ├── errors.py               # Standard AppError exceptions & handlers
│   ├── deps.py                 # Authentication & authorization dependencies
│   ├── security.py             # Clerk JWT verification & share-token helpers
│   ├── jobs.py                 # Asynchronous background job runner
│   ├── schemas/                # Pydantic request & response models
│   ├── routers/                # 7 domain routers for endpoints 1–37
│   ├── services/               # Business logic, satellite extraction & LLM guardrails
│   ├── analysis/               # Mathematical algorithms (anomalies, runs, outlook)
│   └── engine/                 # Two-stage rotation scoring engine
├── data/
│   ├── schema.sql              # PostgreSQL master DDL schema
│   ├── crops.csv               # 8 starter agronomic crops catalog
│   ├── seasons.json            # Kerala planting season windows
│   ├── explainers.json         # Plain-language science cards
│   ├── todo_messages.json      # Fixed "what to do" recommendation lines
│   ├── sources.json            # Earth observation sources metadata
│   ├── fixtures/               # Seed parquet files for offline demo
│   └── cache/                  # Climatological parquet cache
├── migrations/                 # Incremental SQL migration scripts
├── scripts/
│   ├── seed_demo.py            # Seeds the crop catalog (no demo passwords)
│   ├── pull_cell.py            # Fetches NASA POWER data and builds cell climatology
│   ├── check_env.py            # Environment validation script
│   └── smoke.sh                # End-to-end API smoke test
├── tests/                      # Pytest unit & integration test suites
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container definition
└── .env.example                # Local environment template
```

---

## 2. Setup & Execution

### Local Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Replace DATABASE_URL and Clerk placeholders first
python scripts/check_env.py
python scripts/seed_demo.py
uvicorn app.main:app --reload --port 8000
```

The database URL must be a Neon PostgreSQL connection string with TLS enabled. Configure
`CLERK_SECRET_KEY`, `CLERK_ISSUER`, and `CLERK_JWKS_URL` in `backend/.env`; the Clerk
secret key must match the one in `frontend/.env.local`. New users are provisioned in
PostgreSQL on their first authenticated API request. New users default to the `farmer`
role; set trusted roles through Clerk `public_metadata` before the user's first login.

Field onboarding obtains SRTM terrain and SoilGrids estimates from their source
services. Set `EE_PROJECT` and configure Google application-default credentials to
enable MODIS NDVI and GPM IMERG point-series extraction; without Earth Engine access,
the backend retains NASA POWER rainfall and reports the missing NDVI data instead of
generating synthetic observations.

Pre-fetch a NASA POWER cell's historical data and normals before a demo or analysis:
```bash
python scripts/pull_cell.py --lat 9.5 --lon 76.4
```
Use `--refresh` to refetch the provider series and `--years 20` to set the history
window. The script requires network access to NASA POWER.

### Running Tests
```bash
pytest tests/
```
