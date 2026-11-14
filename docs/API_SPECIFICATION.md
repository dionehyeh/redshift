# Field Shift API Specification (v1)

> **Base Path:** `/api/v1`  
> **Format:** JSON Request & Response bodies  
> **Auth:** Clerk session tokens are forwarded by Next.js as bearer tokens and verified by FastAPI using Clerk's issuer and JWKS.

---

## 1. Global Conventions

### 1.1 Standard Error Envelope
All error responses (4xx, 5xx) strictly follow this structure:
```json
{
  "error": {
    "code": "FIELD_NOT_READY",
    "message": "Field profile is still being built",
    "details": {
      "job_id": "j_8f2a"
    }
  }
}
```

### 1.2 Common Error Codes
- `UNAUTHENTICATED` (401): Missing, invalid, or expired Clerk session token.
- `IDENTITY_PROVIDER_UNAVAILABLE` (503): Clerk signing keys or user profile service could not be reached.
- `AUTH_CONFIGURATION` (503): Required Clerk issuer, JWKS, or secret-key configuration is missing.
- `ACCOUNT_CONFLICT` (409): Authenticated Clerk contact is already attached to another local profile.
- `FORBIDDEN` (403): Role or ownership mismatch.
- `NOT_FOUND` (404): Resource does not exist (or belongs to another farmer).
- `FIELD_NOT_READY` (409): Field profile or normals are still building.
- `CROP_REQUIRED` (422): Farmer-led plan request missing target crop.
- `VALIDATION` (422): Malformed request body.
- `DATA_UNAVAILABLE` (503): External satellite source offline and no cached fallback exists.

---

## 2. Complete Endpoints Catalog (1–37)

### Authentication & User Profiles
| # | Method | Path | Auth | Description |
|---|---|---|---|---|
| 1 | Clerk | `/register` | Public | Create an identity using Clerk's signup flow |
| 2 | Clerk | `/login` | Public | Authenticate using Clerk's sign-in flow |
| 3 | `GET` | `/me` | Clerk session | Fetch or provision the current application profile, including preferences |
| 4 | `PATCH` | `/me/prefs` | Clerk session | Update language (en/ml), market toggle, and default-share consent; returns the updated profile |

`GET /me` returns `id`, `name`, `role`, `language`, `contact`, optional `helper_type`,
`market_toggle` (`earn_more`, `play_safe`, or `null`), and
`default_share_consent` (`0` or `1`). `PATCH /me/prefs` accepts any subset of
`language`, `market_toggle`, and `default_share_consent`; send `market_toggle: null`
to clear the planning default. These endpoints use the common error envelope for
unauthenticated requests, invalid preference values, and profile provisioning failures.

### Fields Management
| # | Method | Path | Auth | Description |
|---|---|---|---|---|
| 5 | `POST` | `/fields` | Farmer | Create new field; returns 202 with `job_id` |
| 6 | `GET` | `/fields` | Farmer | List all owned fields with profile readiness status |
| 7 | `GET` | `/fields/{id}` | Farmer | Get full field profile with data sources and confidence |
| 8 | `PATCH` | `/fields/{id}` | Farmer | Edit field parameters or provide manual soil corrections; coordinate changes queue profile rebuilding (202) |
| 9 | `GET` | `/fields/{id}/feasible-crops` | Farmer | Feasible crop list (Suitable, Marginal, Not Suitable) |
| 10 | `GET` | `/fields/{id}/timeline` | Farmer | 52-week climate series and normals (rain, temperature, and NDVI when available) |
| 11 | `GET` | `/fields/{id}/map` | Farmer | GeoJSON polygon/point with elevation & flood layers |
| 12 | `GET` | `/fields/{id}/history` | Farmer | Historical seasons list with outcomes & verified causes |

### Historical Seasons & Likely-Causes Diagnosis
| # | Method | Path | Auth | Description |
|---|---|---|---|---|
| 13 | `POST` | `/fields/{id}/seasons` | Farmer | Log past or completed crop season |
| 14 | `GET` | `/seasons/{id}` | Farmer | Get single season record and review status |
| 15 | `PATCH` | `/seasons/{id}` | Farmer | Update dates, outcome rating, or investment figures |
| 16 | `POST` | `/seasons/{id}/analyze` | Farmer | Trigger background likely-causes diagnostic job |
| 17 | `GET` | `/seasons/{id}/analysis` | Farmer | Get diagnosed findings, stress flags, gaps, and questions |
| 18 | `POST` | `/findings/{id}/review` | Farmer/Mentor | Confirm, correct, or reject a diagnosed finding |

Season analysis reports the actual climatology period, data gaps, and likely causes
from the completed analysis job. If an analysis is not complete, the response does
not invent findings or observations. Findings include a value unit when applicable;
rainfall deviations are percentages and heat deviations are degrees Celsius.
Unavailable source data is reported as a gap and completes the job as
`done_with_gaps`.

### Crop Planning & Scenario Simulation
| # | Method | Path | Auth | Description |
|---|---|---|---|---|
| 19 | `POST` | `/fields/{id}/plans` | Farmer | Generate 3 strategy cards (suggest or farmer-led) |
| 20 | `GET` | `/plans/{id}` | Farmer | Retrieve stored plan with full cards & explanations |
| 21 | `POST` | `/plans/{id}/rescore` | Farmer | Instant re-scoring based on rainfall & temperature sliders |
| 22 | `POST` | `/plans/{id}/choose` | Farmer | Select card; marks as planned season in field history |

### Mentor Consultation & Consent Sharing
| # | Method | Path | Auth | Description |
|---|---|---|---|---|
| 23 | `POST` | `/reports` | Farmer | Create consent snapshot report for student mentor/officer |
| 24 | `GET` | `/reports/{id}` | Farmer/Mentor | Read report snapshot (scrubbed per consent rules) |
| 25 | `POST` | `/reports/{id}/comments` | Mentor/Officer | Post mentor advisory feedback to the farmer |
| 26 | `POST` | `/reports/{id}/revoke` | Farmer | Immediately revoke mentor access to report snapshot |
| 27 | `GET` | `/mentor/inbox` | Mentor/Officer | List shared consultation reports pending review |
| 28 | `GET` | `/helpers` | Farmer | List available student mentors, volunteers, and officers |

### Reference Data & Explainers
| # | Method | Path | Auth | Description |
|---|---|---|---|---|
| 29 | `GET` | `/crops` | Public | Master crops catalog (duration, water needs, windows) |
| 30 | `GET` | `/crops/{id}` | Public | Detailed agronomic parameters for specific crop |
| 31 | `GET` | `/explainers` | Public | List plain-language science cards in requested language |
| 32 | `GET` | `/explainers/{key}` | Public | Get single science card (e.g. NDVI, water balance) |
| 33 | `GET` | `/outlook` | Public | Current 5–8 month seasonal rainfall outlook range |
| 34 | `GET` | `/reference/seasons` | Public | Kerala planting seasons calendar (Virippu, Mundakan, Puncha)|
| 35 | `GET` | `/sources` | Public | Dataset metadata, spatial resolution, and limitations |

### System & Async Jobs
| # | Method | Path | Auth | Description |
|---|---|---|---|---|
| 36 | `GET` | `/jobs/{id}` | Owner | Poll status, step, and progress of background task |
| 37 | `GET` | `/health` | Public | System status, external data connectivity & DEMO_MODE |

When weekly observations are unavailable, the field timeline returns climatological estimates instead. Metrics absent from the climate cache, including NDVI, are omitted rather than fabricated.
