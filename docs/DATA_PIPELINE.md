# Field Shift Data Pipeline & Mathematical Analysis

This specification defines the harmonization, cleaning, normal computation, anomaly detection, and stress flag synthesis algorithms implemented in `backend/app/analysis/core.py`.

---

## 1. Pipeline Stages

```
[1. Locate]       Pin coordinate (lat, lon) -> 0.5° POWER cell; retain point for 250 m data
[2. Pull]         Fetch POWER normals, point MODIS composites, and seasonal IMERG weeks
[3. Clean]        Missing values (-999/-9999) -> NaN; Clip rain to >= 0; Scale NDVI (x0.0001)
[4. Weekly]       Aggregate ISO calendar weeks (week 53 folded into week 52)
[5. Normals]      Compute 52-week mean, std dev, and count (minimum 10 years per week)
[6. Terrain]      SRTM 7x7 neighborhood -> Compute slope %, local relief, and a low-confidence flood indicator
[7. Diagnosis]    Calculate z-scores -> Detect continuous stress runs -> Synthesize findings
[8. Outlook]      Combine weekly normals + current moisture + IMD seasonal outlook range
```

---

## 2. Temporal Rollup & Normals

### 2.1 ISO Week Folding
To ensure consistent 52-week annual indexing across 20+ years:
```python
iso_week = df.index.isocalendar().week.astype(int).clip(upper=52)
```
ISO week 53 is folded into week 52.

### 2.2 Pro-rated Rainfall Sums
For weeks with missing days (e.g. at the start or end of a pull period), rainfall is pro-rated to a 7-day equivalent so partial weeks do not appear artificially dry:
$$\text{Rain}_{\text{weekly}} = \left(\sum \text{Rain}_{\text{daily}}\right) \times \frac{7}{\text{Valid Days}}$$

### 2.3 Normals Calculation & Circular Interpolation
- Normals require at least 10 valid years (`MIN_YEARS = 10`) for a given week.
- Any week with $< 10$ years is marked as NaN and filled via circular interpolation spanning year-end boundaries.

---

## 3. Anomaly Computation & Minimum Variance Floors

### 3.1 Standardized Z-Score
$$Z = \frac{\text{Value} - \mu_{\text{week}}}{\max(\sigma_{\text{week}}, \text{Floor})}$$

### 3.2 Variance Floors
To prevent extreme z-scores during naturally dry or stable periods:
- **Rainfall:** `STD_FLOOR = 5.0 mm`
- **Temperature (Mean & Max):** `STD_FLOOR = 0.3 °C`
- **NDVI:** `STD_FLOOR = 0.03`

---

## 4. Continuous Run Detection & Stress Flags

A finding is triggered only when an anomaly persists for consecutive time steps:

| Indicator | Trigger Condition | Min Duration | Finding Type |
|---|---|---|---|
| **Rain Deficit** | $Z_{\text{rain}} < -1.0$ | $\ge 2$ consecutive weeks | `rain_deficit` |
| **Heat Stress** | $T_{\text{max}} > T_{\text{flower\_max}}$ | $\ge 2$ consecutive weeks | `heat` |
| **Vegetation Dip** | $Z_{\text{ndvi}} < -1.0$ | $\ge 2$ consecutive composites | `ndvi_dip` |
| **Cloud Gap** | Missing / masked NDVI | $\ge 2$ consecutive composites | `cloud_gap` (Data Gap) |
| **Bare Field** | $\text{NDVI} < 0.25$ | $\ge 8$ consecutive weeks | `bare_field` (Fallow window) |

### 4.1 Phenological Stage Weighting
Stress impact depends heavily on crop stage at the time of the event:
$$\text{Severity} = \text{Base Anomaly Deviation} \times \text{Duration (weeks)} \times W_{\text{stage}}$$

- **Flowering:** $W = 1.5$
- **Grain Filling:** $W = 1.3$
- **Establishment:** $W = 1.2$
- **Vegetative:** $W = 1.0$
- **Maturity:** $W = 0.7$

---

## 5. Water Outlook & Stored Soil Moisture

### 5.1 5–8 Month Water Outlook
$$R_{\text{expected}} = \sum_{w=start}^{start+n} \text{NormalRain}_w \times F_{\text{outlook}}$$
Where $F_{\text{outlook}}$ is derived from the latest date-valid IMD seasonal
monsoon bulletin configured for the region. If no current bulletin is available,
the score uses a neutral climatological factor range of $0.85$ to $1.15$, marks
confidence low, and includes an explicit source gap; it does not reuse an expired
forecast.

### 5.2 Stored Soil Moisture at Planting
Dry-season crops (e.g. green gram or sesame sown after monsoon paddy) rely heavily on residual soil water:
$$\text{Available Water} = \text{Effective Rainfall} + \text{Stored Soil Water}$$

- **Farmer Answer Hierarchy:**
  1. Direct answer: `"wet"` ($100\% = 150\text{ mm}$), `"moist"` ($50\% = 75\text{ mm}$), `"dry"` ($0\% = 0\text{ mm}$).
  2. Satellite soil moisture (SMAP/GLDAS) scaled between wilting point ($0.10$) and field capacity ($0.35$).
  3. Default fallback: $30\%$ capacity ($45\text{ mm}$) labeled with **Low Confidence**.

## 6. Runtime Diagnosis Behavior

Season analysis uses the field's cached weekly series and the season's recorded dates.
The analysis selects the matching ISO weeks, computes week-of-year normals from the
available history, and reports rainfall deficits and flowering-stage heat runs only
when the observations and corresponding weekly normals are available. Coverage below
the documented 10-year minimum is surfaced as a data gap.
Repeated analysis updates matching pending findings while preserving findings that
have already been reviewed.

NASA POWER supplies the 20-year weather baseline and cached 0.5-degree daily/weekly
series. With a configured Earth Engine project and application credentials, the
climate loader also samples MODIS MOD13Q1 at the field point and GPM IMERG weekly
rainfall for the selected year or season. IMERG observations are compared with POWER
climatology; weeks without adequate IMERG coverage retain POWER observations. MODIS
composites are quality-filtered and expanded only over their documented 16-day
composite windows. NDVI is cached at an approximately 250 m point key rather than
being shared across a 0.5-degree weather cell.

Field onboarding reads SRTM elevation from the 30 m `srtm30m` service and soil
properties from the ISRIC SoilGrids v2.0 point API. Slope is computed from a local
elevation neighborhood. The flood flag is only a low-confidence local-relief
indicator; it is not an observed flood map. Drainage is an estimate based on
SoilGrids texture and SRTM slope. When a provider has no data, the profile records a
gap and leaves that metric unavailable rather than substituting a regional constant.
Jobs finish as `done_with_gaps` when non-critical providers are unavailable; missing
elevation or climatology prevents crop suitability from being marked ready. The
diagnostic remains deterministic and does not infer pests, disease, or nutrient
deficiencies from satellite data.
