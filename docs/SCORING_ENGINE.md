# Field Shift Rotation Scoring Engine

This document details the deterministic two-stage rotation evaluation engine implemented in `backend/app/engine/scoring.py`.

---

## 1. Core Principles

1. **Deterministic Execution:** The engine is pure Python code. The LLM has zero involvement in scoring, filtering, or ranking.
2. **Two-Stage Architecture:**
   - **Stage 1: Hard Feasibility Filters** (Binary: Can this crop physically grow here this season?)
   - **Stage 2: Multicriteria Factor Scoring** (0–100 continuous scores across 6 agronomic dimensions).
3. **Red Flag Veto Rule:** Any crop with a single factor score $< 40$ (Red Flag) is **strictly barred** from suggested cards (Cards 2 & 3).
4. **Existing Rotation Preservation:** Card 1 **always** presents the farmer's historical or customary rotation crop, regardless of how poorly it scores.
5. **Worst-Case Robustness Ranking:** Crops within a 5-point total score band are ranked by their lowest score across 4 stress scenarios:
   - Rain $-20\%$
   - Rain $+20\%$
   - Temperature $+2\text{ °C}$
   - Rain $-20\%$ with Temperature $+2\text{ °C}$

---

## 2. Stage 1: Hard Filters

| Filter | Rule | Result |
|---|---|---|
| **Elevation** | Elevation outside $[\text{elev\_min}, \text{elev\_max}]$ | `not_suitable` |
| **Temperature** | Mean window temp outside $[T_{\text{min}}, T_{\text{max}}]$ by $> 3\text{ °C}$ | `not_suitable` |
| | Outside by $\le 3\text{ °C}$ | `marginal` |
| **Start Window** | Start week distance to nearest planting window $> 4$ weeks | `not_suitable` |
| | Distance $1$ to $4$ weeks | `marginal` |
| **Duration / Overlap** | Long-duration crops (`long_duration = 1`, $>200$ days like banana, tapioca) skip next season overlap | `suitable` |
| | Overlap with next planting season $> 30$ days | `not_suitable` |
| | Overlap $1$ to $30$ days | `marginal` |

---

## 3. Stage 2: Factor Scoring (0–100)

### 3.1 Water Fit Score
```
effective_rain = window_rain * outlook_factor * slider_rain_factor * 0.75
available      = effective_rain + stored_soil_water_mm
gap            = max(0.0, crop_need_mm - available)
supply         = available + (irrigation_share * gap)
ratio          = (supply / crop_need_mm) * (1 + 0.15 * drought_tolerance)
water_score    = clamp((ratio - 0.3) / 0.5 * 100)
```
- **Waterlogging Penalty:** Subtract $25$ if slider rain $\ge 1.15$, field is flood-prone, and crop waterlogging tolerance is Low.
- **Salinity Penalty:** Subtract $20$ for Low tolerance, $10$ for Medium tolerance if water quality is saline.

### 3.2 Rotation & History Fit Score
Base score begins at **80**:
- Same crop as last season: $-\text{repeat\_penalty}$ (paddy $15$, vegetables/pulses $40$).
- Same crop 3 times in a row: $-15$ additional.
- Same botanical family as last season: $-25$.
- Same family as 2nd-to-last season: $-10$.
- Heavy nitrogen feeder after heavy feeder: $-20$.
- Nitrogen fixer after heavy feeder: $+15$.
- Heavy feeder after nitrogen fixer: $+10$.
- Previous crop failed due to verified pest/disease and same family: $-20$.
- Previous crop failed due to water stress and current outlook is dry: $-10$.

### 3.3 Temperature Fit Score
$$\text{temp\_score} = 100 \times \frac{\text{Weeks within } [T_{\text{min}}, T_{\text{max}}]}{\text{Total Window Weeks}}$$
- **Flowering Heat Stress Penalty:** Subtract $30$ if any week during flowering exceeds $T_{\text{flower\_max}} + \text{offset}$.

### 3.4 Soil Fit & Benefit Score
$$\text{soil\_score} = 0.5 \times \text{Fit} + 0.5 \times \text{Benefit}$$
- **pH Fit:** Inside range: $100$; outside by $\le 0.5$: $70$; further: $40$; unknown: $60$.
- **Drainage Fit:** In flood-prone/poor drainage: High tolerance: $100$; Medium: $70$; Low: $40$.
- **Benefit Base:** Nitrogen fixer: $100$; Neutral: $60$; Heavy feeder: $30$.
- **Bonuses (Capped at 100):** Organic matter bonus ($+10$), Erosion cover on slope ($+10$), Fills bare ground window $\ge 40$ days ($+10$).

### 3.5 Market Fit Score
- High local demand: $85$
- MSP supported: $80$
- Medium demand / few buyers: $60$
- Variable / unknown: $50$
- Limited buyers: $30$

### 3.6 Timing Fit Score
- Zero overlap with next season: $100$
- $1$ to $14$ days overlap: $60$
- $15$ to $30$ days overlap: $30$

---

## 4. Multicriteria Weights & Dynamic Adjustments

### Base Weights (Sum 100)
| Water | Rotation | Temperature | Soil | Market | Timing |
|---|---|---|---|---|---|
| 30 | 25 | 15 | 15 | 10 | 5 |

### Weight Shift Triggers
- **Dry Outlook ($F_{\text{outlook}} < 0.9$):** Water $+10$, Market $-5$, Soil $-5$.
- **Farmer Toggle "Earn More":** Market $+10$, Water $-5$, Rotation $-5$.
- **Farmer Toggle "Play Safe":** Water $+5$, Market $-5$.

Weights are clamped to a minimum of $3$ and normalized to sum to $100$.

---

## 5. Strategy Cards Selection (Cards 1, 2, 3)

1. **Card 1 (Customary Rotation):** Crop the farmer customarily grows or planted last season.
2. **Card Pool for Cards 2 & 3:** Crops passing Stage 1 hard filters with **zero Red Factors** ($f_i \ge 40$), excluding Card 1.
3. **Family Diversity:** Card 2 and Card 3 must belong to different botanical families from each other and from Card 1.
4. **"Holds Up Best" Badge:** Awarded to the card with the highest worst-case score across the 4 stress scenarios if it leads by $\ge 5$ points and has no red factor.
