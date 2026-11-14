# Backend Implementation Guide

This guide details the structural contracts, design patterns, and operational rules for implementing all components in the `backend/` directory.

---

## 1. Domain Services Responsibilities

| Service | File | Primary Responsibility | External Dependencies |
|---|---|---|---|
| `field_service` | `app/services/field_service.py` | Create fields, trigger onboarding jobs, compute slope & flood flag from SRTM, update manual farmer soil corrections | SRTM DEM, SoilGrids |
| `climate_service` | `app/services/climate_service.py` | Fetch NASA POWER, IMERG, MODIS NDVI; aggregate weekly; write/read Parquet cell cache | `requests`, `earthaccess`, `xarray` |
| `analysis_service` | `app/services/analysis_service.py` | Run 20-year normals, compute z-scores, detect stress runs, format findings | `app.analysis.core` |
| `scoring_service` | `app/services/scoring_service.py` | Apply hard filters, calculate 6 factor scores, rank 3 cards | `app.engine.scoring` |
| `plan_service` | `app/services/plan_service.py` | Generate plans, handle debounced slider rescoring, record chosen plan | `scoring_service`, `text_service` |
| `text_service` | `app/services/text_service.py` | Invoke LLM with structured JSON, validate numerical output, fallback to template sentences | Gemini/OpenAI API |
| `report_service` | `app/services/report_service.py` | Create scrubbed consent snapshots, generate share tokens, enforce expiration & revocation | `app.security` |
| `reference_service` | `app/services/reference_service.py` | Serve master crops catalog, localized explainers, seasonal outlooks, data sources | JSON / CSV files |

---

## 2. Router & Schemas Mapping

All routers must reside in `app/routers/` and use Pydantic schemas from `app/schemas/`:

```
app/routers/auth.py       <-> app/schemas/auth.py       (Endpoints 1–4)
app/routers/fields.py     <-> app/schemas/fields.py     (Endpoints 5–12)
app/routers/seasons.py    <-> app/schemas/seasons.py    (Endpoints 13–18)
app/routers/plans.py      <-> app/schemas/plans.py      (Endpoints 19–22)
app/routers/reports.py    <-> app/schemas/reports.py    (Endpoints 23–28)
app/routers/reference.py  <-> app/schemas/reference.py  (Endpoints 29–35)
app/routers/system.py     <-> app/schemas/system.py     (Endpoints 36–37)
```

---

## 3. Database & Transaction Principles

1. **Explicit Transaction Boundaries:** Database writes must occur inside context-managed transactions (`with get_db() as db:`).
2. **Never Write in Analysis:** Analysis functions in `app/analysis/` and `app/engine/` must be pure functions with zero database side effects.
3. **No Raw SQL in Routers:** Routers only call service methods; SQL queries are restricted to service/repository functions.
4. **PostgreSQL:** The Neon schema is initialized from `data/schema.sql`; inserts that need generated IDs use `RETURNING id`. Keep SQL portable to PostgreSQL and use `ON CONFLICT` instead of SQLite-only upsert syntax.

---

## 4. Testing Requirements

- **Unit Tests (`tests/test_analysis.py`):**
  - Verify missing flag (-999) replacement with `np.nan`.
  - Verify ISO week 53 folding into week 52.
  - Verify circular interpolation over year-end boundaries.
  - Verify stress run detection for simulated 3-week drought.
- **Engine Tests (`tests/test_engine.py`):**
  - Verify nitrogen fixer outscoring heavy feeder after heavy feeder.
  - Verify red flag veto rule (crop with factor score $<40$ excluded from Cards 2 & 3).
  - Verify slider rainfall monotonicity.
- **Integration Tests (`tests/test_api_flow.py`):**
  - Execute the authenticated end-to-end flow: Clerk session -> create field -> analyze season -> generate plan -> rescore -> choose card -> share report.
