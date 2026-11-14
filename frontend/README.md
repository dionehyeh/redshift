# Field Shift Frontend Client

Next.js 14+ (App Router) mobile-first Progressive Web Application styled with Tailwind CSS, shadcn/ui components, and bilingual localization (English and Malayalam).

---

## 1. Directory Structure

```
frontend/
├── app/
│   ├── layout.tsx                   # Root HTML shell, fonts & providers
│   ├── globals.css                  # Tailwind styles & semantic risk tokens
│   ├── page.tsx                     # Landing page & login redirect
│   ├── profile/page.tsx             # App profile and saved user preferences
│   ├── auth/redirect/page.tsx       # Provision profile and redirect by role
│   ├── about/page.tsx               # Data transparency & limitations
│   ├── (auth)/                      # Authentication route group
│   ├── (farmer)/                    # Farmer operations route group
│   ├── (mentor)/                    # Consultation review route group
│   └── api/                         # Next.js BFF proxy routes
├── components/
│   ├── shell/                       # AppShell, TopBar, BottomNav, DataBadge
│   ├── ui/                          # shadcn/ui primitives (Radix UI)
│   ├── risk/                        # RiskBadge, ConfidenceTag, SourceNote
│   ├── fields/                      # FieldCard, FieldMap, ProfileList, FeasibleList
│   ├── season/                      # TimelineChart, FindingItem, SeasonForm
│   ├── plan/                        # PlanCard, ScenarioPanel, ChangeChips
│   ├── report/                      # ShareDialog, ReportView, CommentBox
│   └── common/                      # JobProgress, ExplainerSheet, ErrorBanner
├── lib/
│   ├── api.ts                       # Browser API client (proxied)
│   ├── server-api.ts                # Server Component client (with Clerk session token)
│   ├── types.ts                     # OpenAPI generated TypeScript types
│   ├── schemas.ts                   # Client-side zod validation schemas
│   ├── hooks.ts                     # TanStack Query custom hooks
│   └── format.ts                    # Indian locale & date formatters
├── messages/
│   ├── en.json                      # English localization strings
│   └── ml.json                      # Malayalam localization strings
├── middleware.ts                    # Route protection & session redirect
├── package.json                     # Node.js dependencies
├── tsconfig.json                    # TypeScript compiler options
├── next.config.ts                   # Next.js configuration
├── tailwind.config.ts               # Tailwind CSS theme configuration
└── components.json                  # shadcn/ui configuration
```

---

## 2. Setup & Execution

### Local Development
```bash
npm install
# Add your Clerk keys to .env.local (template: .env.example)
npm run dev
```
Access the client application at `http://localhost:3000`.

Set `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` in
`frontend/.env.local`. The backend also needs the same Clerk secret key, its issuer URL,
and its JWKS URL in `backend/.env`. Client API calls pass a Clerk session token through
the Next.js proxy; the FastAPI backend verifies it against Clerk's JWKS.

After Clerk sign-in or sign-up, the frontend calls `GET /api/me` through the proxy to
provision/read the Field Shift profile and routes by the trusted application role.
`/profile` loads that profile and saves preferences through `PATCH /api/me/prefs`.

### Type Generation from FastAPI OpenAPI
With the backend running on `http://localhost:8000`:
```bash
npx openapi-typescript http://localhost:8000/openapi.json -o lib/types.ts
```
