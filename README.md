# Field Shift: Adapting Farms with NASA Data

> **NASA Space Apps Challenge 2026**  
> **Pilot Region:** Kerala, India (One demonstration field, 6–8 rotational crops)

Field Shift is an agricultural decision-support platform designed to help smallholder farmers adapt planting strategies using 20+ years of NASA Earth observations harmonized with local ground truth (Soil Health Cards, state weather stations, farmer corrections).

---

## 1. Project Philosophy & Architecture Principles

1. **NASA Data is the Global Base Layer:** Global coverage (POWER, GPM/IMERG, MODIS NDVI, SRTM, SMAP/GLDAS) enables immediate deployment for any field coordinate.
2. **Local Data Narrowing:** State data (IMD gridded rainfall, Soil Health Cards, KAU package of practices) and direct farmer corrections refine coarse satellite observations.
3. **Weekly Temporal Harmonization:** All data streams are resampled into standardized weekly steps (weeks 1–52) compared against 10–20 year climatological normals.
4. **Deterministic Fact Computation:** All anomalies, stress indicators, and crop rotation suitability scores are computed deterministically in code. The LLM is used **strictly for natural language phrasing and translation**, never generating or adjusting numbers.
5. **Auditable Metadata:** Every data point displays its data source, spatial resolution, fetch timestamp, and confidence score.
6. **Supportive, Not Authoritative:** The system acts as a decision-support advisory tool. It does not replace farmer judgment or certified agronomic expertise.

---

## 2. Monorepo Structure

```
nasa/
├── docs/                      # Architectural, agronomic, API & operational documentation
│   ├── ARCHITECTURE.md        # Full system architecture and component interactions
│   ├── API_SPECIFICATION.md   # Complete endpoints specification (Endpoints 1–37)
│   ├── DATA_PIPELINE.md       # Satellite & ground data harmonization and analysis
│   ├── SCORING_ENGINE.md      # Deterministic rotation scoring rules & formulas
│   ├── FRONTEND_SPECS.md      # UI pages, state machines, component specs
│   ├── DATABASE_AND_STORAGE.md# Neon PostgreSQL schema, tables, caching
│   ├── SECURITY_AND_OPERATIONS.md # Auth, privacy, consent, rate limiting, deployment
│   ├── NASA_DATASETS_GUIDE.md # Dataset catalog, access tiers, and product IDs
│   └── ROADMAP.md             # Implementation phases & build order
│
├── backend/                   # FastAPI Python backend service
│   ├── app/
│   │   ├── main.py            # FastAPI entry point & middleware wiring
│   │   ├── config.py          # Environment settings
│   │   ├── db.py              # Neon PostgreSQL connection & transaction management
│   │   ├── errors.py          # Standardized error definitions
│   │   ├── deps.py            # Auth & role dependency injection
│   │   ├── security.py        # Clerk JWT verification & share-token helpers
│   │   ├── jobs.py            # Async onboarding & analysis job runner
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── routers/           # Auth, fields, seasons, plans, reports, reference, system
│   │   ├── services/          # Business logic & external data orchestration
│   │   ├── analysis/          # Core mathematical analysis (anomalies, stress, outlook)
│   │   └── engine/            # Two-stage rotation scoring engine
│   ├── data/                  # Reference CSVs, JSON fixtures & parquet caches
│   ├── migrations/            # SQL migration scripts
│   ├── scripts/               # Seed scripts, data downloaders, smoke test
│   ├── tests/                 # Unit & integration test suites
│   ├── requirements.txt       # Python dependencies
│   └── README.md
│
├── frontend/                  # Next.js 14+ (App Router) TypeScript frontend
│   ├── app/                   # App Router pages and proxy routes
│   │   ├── (auth)/            # Login & Register views
│   │   ├── (farmer)/          # Farmer dashboard, fields, seasons, plans, reports
│   │   ├── (mentor)/          # Student mentor & officer inbox & review views
│   │   ├── about/             # "About This Analysis" & data transparency
│   │   └── api/               # Server-side proxy & authentication routes
│   ├── components/            # UI components (Shell, Risk, Fields, Season, Plan, Report)
│   ├── lib/                   # API clients, zod schemas, hooks, formatters
│   ├── messages/              # Localization files (en.json, ml.json for Malayalam)
│   ├── package.json           # Frontend package dependencies
│   ├── tailwind.config.ts     # Styling and semantic risk token configuration
│   ├── Dockerfile             # Container configuration
│   └── README.md
│
├── docker-compose.yml         # Container orchestration for local / offline demo
├── .env.example               # Root environment templates
└── README.md                  # Project overview (this file)
```

---

## 3. Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js (App Router), React 18/19, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Recharts, Leaflet (`react-leaflet`), `next-intl` |
| **Backend** | Python 3.10+, FastAPI, Pydantic v2, Neon PostgreSQL (`psycopg2`), Clerk token verification, `pandas`, `numpy`, `xarray`, `pyarrow` |
| **Earth Data Tools** | `earthaccess` (NASA Earthdata), Google Earth Engine API (`earthengine-api`), NASA POWER REST API |
| **AI / Natural Language** | Gemini / OpenAI API (Optional, strictly for narrative formulation with numeric validation and deterministic template fallbacks) |

---

## 4. Quickstart Guide

### Option A: Local Development

1. **Backend Setup:**
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   cp .env.example .env
   # Fill DATABASE_URL and Clerk placeholders in backend/.env before starting.
   python scripts/seed_demo.py
   uvicorn app.main:app --reload --port 8000
   ```
   API Documentation will be live at `http://localhost:8000/docs`.

2. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   # Copy frontend/.env.example to frontend/.env.local, then fill in the Clerk keys.
   npm run dev
   ```
   Web interface will be live at `http://localhost:3000`.

### Option B: Docker Compose (Neon and Clerk credentials required)

```bash
docker-compose up --build
```

---

## 5. Documentation Directory

Detailed implementation guides are located in the [`docs/`](./docs/) directory:
- [System Architecture](./docs/ARCHITECTURE.md)
- [API Specification (Endpoints 1–37)](./docs/API_SPECIFICATION.md)
- [Data Pipeline & Harmonization](./docs/DATA_PIPELINE.md)
- [Scoring Engine & Rotation Formulas](./docs/SCORING_ENGINE.md)
- [Frontend Pages & UI Components](./docs/FRONTEND_SPECS.md)
- [Database Schema & Parquet Caching](./docs/DATABASE_AND_STORAGE.md)
- [Security, Privacy & Consent](./docs/SECURITY_AND_OPERATIONS.md)
- [NASA Datasets & Verification Guide](./docs/NASA_DATASETS_GUIDE.md)
- [Build Roadmap & Verification Milestones](./docs/ROADMAP.md)
