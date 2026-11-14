# Field Shift Security, Privacy & Operational Architecture

This document defines the data security safeguards, privacy controls, consent-driven snapshot sharing, and operational runtime practices for Field Shift.

---

## 1. Authentication & Session Security

### 1.1 Clerk Authentication
- Clerk manages signup, sign-in, session lifetime, and sign-out in the Next.js frontend.
- The frontend obtains a Clerk session token server-side and forwards it to FastAPI as a bearer token. No custom password handling or application-issued JWTs are used.
- FastAPI verifies the token's RS256 signature against `CLERK_JWKS_URL` and validates its `CLERK_ISSUER`.
- `ALLOWED_ORIGINS` must include the exact frontend origin(s); the backend also checks the token's `azp` against this list.
- `CLERK_SECRET_KEY` is used server-side to fetch a Clerk user profile when provisioning a local application profile. Store the key in both backend and frontend server environments; never expose it with a `NEXT_PUBLIC_` prefix.
- Clerk `public_metadata.role` is the trusted source for elevated application roles. New users default to `farmer`; do not authorize from `unsafe_metadata`.
- Existing SQLite accounts are not automatically linked to Clerk accounts. Link/import them using a separately verified migration before production cutover.

---

## 2. Privacy & Granular Consent Snapshots

Smallholder farmer data privacy is governed by four core tenets:

1. **Farmer Data Sovereignty:** The farmer completely owns their field coordinates, soil measurements, and historical harvest yields.
2. **Selective Disclosure:** When requesting consultation ("Get Help"), the farmer checks only the categories they consent to share:
   - `field_profile` (elevation, slope, soil pH)
   - `history` (previous seasons & yields)
   - `cards` (generated strategy cards)
   - `findings` (diagnosed stress weeks)
3. **Immutable Scrubbed Snapshots:**
   - Mentors do not receive real-time database access to the farmer's account.
   - The system generates an immutable JSON snapshot containing **only** consented fields.
   - Exact coordinates and farmer contact info are scrubbed by default.
4. **Time-Limited Expiry & Immediate Revocation:**
   - Reports automatically expire after 7, 14, or 30 days.
   - The farmer can tap "Stop Sharing" at any time, instantly revoking mentor access.

---

## 3. Rate Limiting & Denial of Service Protection

| Endpoint Group | Threshold | Mechanism |
|---|---|---|
| Clerk sign-in | Configure limits in Clerk Dashboard | Clerk abuse protection |
| `POST /fields/{id}/plans` | 10 creations / hour per field | Field lock |
| `POST /plans/{id}/rescore` | 120 calls / min per user | In-memory token bucket |
| `GET /jobs/{id}` | 1 poll / 2 seconds | Client interval clamp |

---

## 4. LLM Guardrails & Numeric Validation

When AI is enabled (`LLM_API_KEY` present), generated narrative phrasing must pass validation before being stored or displayed:

1. **No External Numbers:** The backend extracts all numerical tokens from the LLM response. If any number is not present in the original input JSON payload, the response is discarded.
2. **Prohibited Language:** Phrases such as "guarantee", "will definitely yield", "best crop", or specific chemical fertilizer/pesticide dosages are banned.
3. **Instant Template Fallback:** On validation rejection or API timeout ($>10\text{ s}$), the app serves deterministic localized string templates. The app functions completely with LLM disabled (`LLM_API_KEY` unset).

---

## 5. Audit Logging

Every security, consultation, and data sharing event is recorded in the `audit_log` table:
- Report creation & consent payload
- Mentor view timestamp
- Mentor comment submission
- Farmer report revocation
- Manual soil or cause overrides
