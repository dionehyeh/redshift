# Field Shift Frontend Specification & UI Architecture

This document defines the page layouts, UI components, state machines, design tokens, and accessibility standards for the Next.js (App Router) client.

---

## 1. Complete Route Hierarchy

```
frontend/app/
├── (auth)/
│   ├── login/page.tsx               # Clerk sign-in
│   └── register/page.tsx            # Clerk sign-up
├── auth/redirect/page.tsx           # Load app profile and route by trusted role
├── (farmer)/
│   ├── layout.tsx                   # Farmer AppShell & navigation guard
│   ├── fields/
│   │   ├── page.tsx                 # Fields catalog with profile status cards
│   │   ├── new/page.tsx             # Interactive Leaflet pin-drop field onboarding
│   │   └── [id]/
│   │       ├── page.tsx             # Field Profile, Feasible Crops & History tabs
│   │       ├── seasons/new/page.tsx # Past season outcome & loss logger
│   │       └── plan/new/page.tsx    # Strategy initiator (Suggest vs Farmer-led)
│   ├── seasons/[id]/page.tsx        # Likely-causes diagnostic report & timeline
│   ├── plans/[id]/page.tsx          # 3 Plan cards with interactive sliders
│   └── reports/[id]/page.tsx        # Consultation status & active mentor comments
├── (mentor)/
│   ├── layout.tsx                   # Mentor AppShell & verification badge
│   ├── inbox/page.tsx               # Queue of shared consultation reports
│   └── reports/[id]/page.tsx        # Read-only snapshot & advisory comment box
├── about/page.tsx                   # Data transparency, resolution & limitations
└── api/
    └── [...path]/route.ts           # Server-side proxy with Clerk session token
```

---

## 2. Page Specifications & Interactions

### 2.1 Add Field (`/fields/new`)
- **Map Pin-Drop:** Client-side Leaflet component with draggable pin and GPS geolocation button.
- **Inputs:** Field name, optional area (hectares), water source (Rain-fed, Borewell, Canal), water quality (Good, Saline, Unsure).
- **Behavior:** Submits to `POST /fields`, receives `202 Accepted` with `job_id`, and transitions to `JobProgress` tracker until status is `done`.

### 2.2 Field Detail & Feasible Crops (`/fields/[id]`)
- **Profile Tab:** Elevation, slope, flood-prone flag, soil pH, and drainage class. Each metric displays its `ConfidenceTag` and `SourceNote`. Farmers can manually correct any value via `PATCH /fields/{id}`.
- **Feasible Crops Tab:** Categorized into Suitable, Marginal, and Not Suitable with clear agronomic explanations (e.g. "Tea: Elevation too low").
- **History Tab:** Chronological seasons with outcomes, verified causes, and mentor verification tags.

### 2.3 Likely-Causes Diagnostic Report (`/seasons/[id]`)
- **Timeline Chart:** Recharts multi-line chart comparing rainfall, temperature, and NDVI against 20-year normals. Gaps (monsoon cloud cover) break the line explicitly rather than dropping to zero.
- **Diagnosed Findings:** Cards detailing deviation percentages, duration, and crop stage impact.
- **Human Review Actions:** Farmers or mentors can Confirm, Correct (select alternate cause), or Reject any finding.

### 2.4 Plan Cards & What-If Sliders (`/plans/[id]`)
- **Scenario Controls (Sticky Top):**
  - Rainfall slider: $-30\%, -20\%, -10\%, -5\%, \text{Expected}, +5\%, +10\%, +20\%$.
  - Temperature slider: $-1\text{ °C}, \text{Expected}, +1\text{ °C}, +2\text{ °C}, +3\text{ °C}$.
  - Toggle: "Earn More" vs "Play Safe".
  - "Reset to Expected" button.
- **Three Cards Layout:**
  - Card 1: Customary / Historical Rotation.
  - Card 2: Highest-scoring alternative passing hard filters and red flag checks.
  - Card 3: Second alternative (guaranteed different botanical family).
- **Card Elements:** Verdict label, 6 factor risk badges, "Holds up best" tag, narrative why/risks/watch-for sections, and expandable "Needs Local Review" checklist.

---

## 3. Design Tokens & Semantic Risk Badges

### 3.1 Color Palette
Semantic risk colors must meet WCAG 2.1 AA contrast requirements ($\ge 4.5:1$):
```css
:root {
  --good: #1f7a4d;     /* Green 65-100 */
  --good-bg: #e6f4ec;
  --watch: #a15c00;    /* Amber 40-64 */
  --watch-bg: #fdf1dc;
  --risk: #b42318;     /* Red <40 */
  --risk-bg: #fde8e6;
}
```

### 3.2 Non-Color Dependent Communication
To accommodate color-blind users and low-contrast sunlight conditions:
- **Green:** Accompanied by `CheckCircle2` icon and the word "Looks fine".
- **Amber:** Accompanied by `AlertTriangle` icon and the word "Watch this".
- **Red:** Accompanied by `XCircle` icon and the word "High risk".

---

## 4. Mobile & Touch-First Guidelines
- **Tap Targets:** Minimum height of $44\text{ px}$ (`h-11` or `h-12`).
- **Typography:** Minimum $16\text{ px}$ for body text; card titles $\ge 24\text{ px}$.
- **Bottom Sheets:** Complex explainers load in mobile drawer sheets (`Sheet`) rather than tooltips.
- **Debounced Sliders:** Slider interactions are debounced by $300\text{ ms}$; existing cards remain visible with a subtle loading indicator during re-score.
