# Frontend Implementation Guide

This guide covers the Next.js frontend, Clerk authentication, the backend proxy, and the client state patterns.

---

## 1. Authentication & Backend Proxy

1. `ClerkProvider` wraps the application, while Clerk middleware protects all routes except the landing, sign-in, sign-up, and about pages.
2. The sign-in and sign-up pages use Clerk components. Session lifecycle and sign-out are managed by Clerk.
3. `app/api/[...path]/route.ts` proxies browser API requests to `API_BASE_URL/api/v1/*` and attaches the Clerk session token as a bearer token. Browser code uses same-origin `/api/v1/*` URLs; backend URLs and tokens are not exposed to the browser.
4. `lib/server-api.ts` obtains the same session token for Server Component data requests.
5. FastAPI verifies Clerk tokens using the configured issuer and JWKS URL. The backend provisions a local application profile on first use.
6. `/auth/redirect` calls `GET /api/me` after sign-in/sign-up and redirects using the backend's trusted role. `/profile` reads the same profile and persists preferences through `PATCH /api/me/prefs`.

Configure `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, the Clerk sign-in/sign-up paths, and `API_BASE_URL` in `frontend/.env.local`. The backend needs the same Clerk secret key plus `CLERK_ISSUER` and `CLERK_JWKS_URL`.
API mocks are disabled by default. Set `NEXT_PUBLIC_USE_MOCK_API=true` only for local UI work without a running backend; mocks are used only for failed GET network requests, never for API error responses or mutations.

---

## 2. Server vs Client Component Boundaries

| Component / Page | Rendering Strategy | Reason |
|---|---|---|
| `app/(farmer)/fields/page.tsx` | Server Component | High-speed initial data fetch directly to backend via `serverApi()` |
| `app/(farmer)/fields/[id]/page.tsx` | Server Component | Fast initial profile render |
| `components/fields/FieldMap.tsx` | Client Component (`ssr: false`) | Leaflet requires access to browser `window` object |
| `components/plan/ScenarioPanel.tsx` | Client Component | Real-time slider events and keyboard accessibility |
| `components/season/TimelineChart.tsx` | Client Component | Interactive SVG rendering via Recharts |
| `components/common/JobProgress.tsx` | Client Component | Continuous TanStack Query polling every 2 seconds |

---

## 3. State Management & Debouncing

### Plan Scenario Sliders (`useRescore` Hook)
- Rainfall and temperature sliders maintain local client state.
- Changes trigger a **300 ms debounce timer** before invoking `POST /plans/{id}/rescore`.
- While the background rescore query is in flight, `placeholderData` keeps existing strategy cards visibly mounted to prevent UI flickering.
- A subtle indicator signals that score recalculation is underway.

---

## 4. Accessibility & Multi-Sensory Risk Communication

1. **Traffic Light Safeguards:** Color alone is never used to convey information. Every risk score is presented as:
   - A distinct semantic color background
   - A distinct Lucide SVG icon (`CheckCircle2`, `AlertTriangle`, `XCircle`)
   - A distinct translated word ("Looks fine", "Watch this", "High risk")
2. **Touch Targets:** Minimum dimensions of $44 \times 44\text{ px}$ for all clickable buttons and toggles.
3. **Malayalam Font Support:** High-legibility font fallback (`Noto Sans Malayalam`) configured with `font-display: swap` to prevent layout shift.
