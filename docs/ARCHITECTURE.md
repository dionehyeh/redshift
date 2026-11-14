# Field Shift System Architecture

## 1. System Overview

Field Shift is architected as a decoupled monorepo composed of a Next.js (App Router) frontend and a Python FastAPI backend, supported by Neon PostgreSQL and disk-cached climatological datasets (Parquet).

```
   Browser Client (Next.js PWA)                     External Data Providers
 ┌───────────────────────────────────┐            ┌─────────────────────────────┐
 │  Onboarding · Field Profile       │            │  NASA POWER (Climatology)   │
 │  Past Season Diagnosis            │            │  GPM / IMERG (Precipitation)│
 │  Plan Cards (3 Rotations)         │            │  MODIS MOD13Q1 (NDVI)       │
 │  Interactive Scenario Sliders     │            │  SRTM GL1 (Elevation/Slope) │
 │  Mentor Review & Consent Panel    │            │  ISRIC SoilGrids / IMD Data │
 └─────────────────┬─────────────────┘            └──────────────┬──────────────┘
                   │ HTTPS / Same-Origin                         │
                   │ Clerk session + JSON                        │
 ┌─────────────────▼─────────────────┐                           │
 │  Next.js Server Proxy (BFF)       │                           │
 │  - /api/[...path] Catch-all       │                           │
 │  - Clerk session token forwarding│                           │
 │  - SSR & Server Components Fetch  │                           │
 └─────────────────┬─────────────────┘                           │
                   │ Internal Network                            │
                   │ Authorization: Bearer <JWT>                 │
 ┌─────────────────▼─────────────────────────────────────────────▼──────────────┐
 │  FastAPI Application Layer (/api/v1)                                         │
 │                                                                              │
 │  Routers:                                                                    │
 │  ├── auth.py          (Current profile and preferences)                      │
 │  ├── fields.py        (Profiles, feasible crops, timeline, map, history)     │
 │  ├── seasons.py       (Log seasons, run analysis, review findings)           │
 │  ├── plans.py         (Generate cards, scenario rescore, plan selection)     │
 │  ├── reports.py       (Consent snapshots, mentor comments, revocation)       │
 │  ├── reference.py     (Crops, explainers, seasonal outlooks, data sources)   │
 │  └── system.py        (Health checks, async job polling)                     │
 │                                                                              │
 │  Services & Domain Engines:                                                  │
 │  ├── field_service.py    (SRTM slope, soil texture, flood-prone flagging)    │
 │  ├── climate_service.py  (Earthdata/POWER pulls, weekly rollup, cell cache)  │
 │  ├── analysis_service.py (Z-score anomalies, runs, stress flag synthesis)   │
 │  ├── scoring_service.py  (Hard filters, 6 factor scores, 3 card ranking)     │
 │  ├── text_service.py     (LLM explanation, numerical guardrail validator)    │
 │  └── report_service.py   (Time-limited snapshot consent & access logging)    │
 │                                                                              │
 │  Async Job Worker (BackgroundTasks / RQ):                                    │
 │  - Onboarding pipeline: Terrain -> Soil -> Normals -> Feasible crops         │
 │  - Season analysis: Season weekly pull -> Anomaly detection -> Stress flags  │
 └─────────────────┬─────────────────────────────────────────────┬──────────────┘
                   │                                             │
          ┌────────▼────────┐                           ┌────────▼────────┐
          │ Neon PostgreSQL │                           │ Parquet Cache   │
          │  (TLS)          │                           │ (Per Grid Cell) │
          │  Users, Fields, │                           │ 20-Year Weekly  │
          │  Seasons, Plans │                           │ Series & Normal │
          └─────────────────┘                           └─────────────────┘
```

---

## 2. Key Architecture Design Decisions

### 2.1 Clerk Authentication & Backend-for-Frontend (BFF) Proxy
- The Next.js frontend acts as a thin proxy for client-side API requests.
- **Authentication:** Clerk manages identity and sessions. The Next.js server obtains Clerk session tokens and forwards them to FastAPI; FastAPI verifies their signature and issuer using Clerk JWKS.
- **Roles:** The backend provisions local application profiles by Clerk user ID. Elevated roles come from trusted Clerk `public_metadata`; new users default to `farmer`.
- **Network Isolation:** The FastAPI backend URL is never exposed to public DNS or client-side bundles; requests pass server-to-server.
- **CORS Mitigation:** Eliminates browser CORS configuration between separate development and production domains.

### 2.2 Deterministic Computation vs. LLM Natural Language Generation
- **Strict Separation of Concerns:**
  - Code calculates all facts (anomalies, stress flags, water-need gaps, rotation history penalties, factor scores).
  - The LLM **never** calculates, changes, or estimates numbers.
  - LLM input is restricted to a structured JSON payload containing calculated facts.
  - The backend runs a regex numerical validator (`validate_explanation`) on LLM output. If an unrecognized number or prohibited word (e.g., "guarantee", "will definitely") is detected, the system immediately rejects the output and falls back to deterministic localized sentence templates.

### 2.3 Shared Climatological Cell Caching
- Weather data (POWER, IMERG) is coarse (10–50 km).
- Rather than re-downloading 20 years of weather data for adjacent farms, data is cached by geographical grid cell IDs (e.g., `09.5N_076.5E`).
- Fields within the same grid cell reference the identical precomputed Parquet series and climatological normals, reducing NASA API traffic by >95%.

### 2.4 Asynchronous Job Execution with Graceful Fallbacks
- Heavy data fetching (POWER API, Earthdata Search) runs asynchronously.
- Long-running operations return `202 Accepted` with a `job_id`.
- If an upstream service (e.g., SoilGrids or Earthdata) times out, the step marks itself `failed`, the pipeline continues with secondary fallbacks (e.g., district Soil Health Card defaults or global averages), and the job finishes as `done_with_gaps`.
- The field remains fully operable with transparent low-confidence tags.
