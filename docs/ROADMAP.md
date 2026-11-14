# Field Shift Build Roadmap & Verification Milestones

This document defines the 10-phase build sequence, deliverables, verification gates, and feature cut list.

---

## 1. Phased Build Sequence

| Phase | Focus Area | Deliverables | Verification Gate |
|---|---|---|---|
| **0. Setup** | Accounts & Tooling | Earthdata login, virtualenvs, dependencies pinned | `scripts/check_env.py` passes |
| **1. Data Pull Smoke** | Satellite Verification | 1 real pull each (POWER, IMERG, MODIS, SRTM) | Fixtures saved in `data/fixtures/` |
| **2. Core Engines** | Mathematical Foundation | `analysis/core.py` and `engine/scoring.py` | Unit tests pass; worked example matches |
| **3. Persistence** | Database & Seeds | Neon PostgreSQL schema applied, `seed_demo.py` | Crop catalog seeded; identities managed by Clerk |
| **4. Backend API** | FastAPI Routers | Endpoints 1–37 implemented | Integration tests pass; `/docs` renders |
| **5. Frontend Shell** | Next.js Base Setup | BFF proxy, Clerk auth, AppShell, Risk badges | Sign-in & Field catalog render |
| **6. Core Screens** | Farmer Experience | Field detail, Diagnosis report, 3 Plan cards, Sliders | Interactive rescoring works without reload |
| **7. Consultation** | Mentor & About | Share dialog, Consent scrub, Mentor inbox | Mentor can post comment |
| **8. Localization** | Language & A11y | English & Malayalam strings, contrast verification | Screen reader & mobile viewport test pass |
| **9. Rehearsal** | Demo Readiness | 3-minute pitch rehearsal, offline video backup | `scripts/smoke.sh` passes end-to-end |

---

## 2. API Build Sequence (Inside Phase 4)

1. **Authentication:** Clerk sign-in/sign-up and profile endpoints (`/me`, `/me/prefs`)
2. **Reference Data:** Endpoints 29–35, 37 (`/crops`, `/explainers`, `/outlook`, `/reference/seasons`, `/sources`, `/health`)
3. **Fields & Background Jobs:** Endpoints 5–12, 36 (`/fields`, `/feasible-crops`, `/timeline`, `/map`, `/history`, `/jobs/{id}`)
4. **Historical Seasons & Diagnosis:** Endpoints 13–18 (`/seasons`, `/analyze`, `/analysis`, `/findings/review`)
5. **Crop Planning & Rescoring:** Endpoints 19–22 (`/plans`, `/rescore`, `/choose`)
6. **Consultation & Mentor Reviews:** Endpoints 23–28 (`/reports`, `/comments`, `/revoke`, `/mentor/inbox`, `/helpers`)

---

## 3. Graceful Feature Cut List (If Time Runs Short)

If build time is constrained, cut features in this precise order:
1. Malayalam explainers beyond the core 6 concepts (fall back to English).
2. Advanced GeoJSON map layers (keep simple pin drop).
3. Dedicated Officer role (merge into single Student Mentor role).
4. "Holds Up Best" comparative badge (retain raw robustness scores).
5. Mentor comment threads (retain static advisory report).
6. Season timeline Recharts chart (fall back to structured findings list).

**Strict Non-Negotiables (Never Cut):**
- Three plan strategy cards (customary + 2 alternatives).
- Rainfall and temperature scenario sliders.
- Confidence tags on all estimates.
- "Estimates, not guarantees" warning label.
- Selective consent sharing dialog.
