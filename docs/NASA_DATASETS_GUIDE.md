# Field Shift NASA Earth Observations & Datasets Guide

This document catalogs every satellite and in-situ dataset utilized by Field Shift, detailing its purpose, access methods, spatial/temporal resolutions, and operational fallbacks.

---

## 1. Datasets Catalog

| Dataset | Provider & Product ID | Spatial / Temporal Resolution | Pipeline Usage | Fallback Strategy |
|---|---|---|---|---|
| **NASA POWER** | Langley Research Center (`AG` Community) | $\sim 50\text{ km}$ ($0.5^\circ$), Daily | 20-year weather climatology and gap fallback for rainfall observations | Atomic Parquet cache by grid cell |
| **GPM / IMERG** | NASA GES DISC (`NASA/GPM_L3/IMERG_V07` in Earth Engine) | $\sim 11\text{ km}$, 30-minute | Weekly rainfall observations for timelines and season diagnosis | NASA POWER observations; coverage gaps remain explicit |
| **MODIS NDVI** | LP DAAC (`MODIS/061/MOD13Q1` in Earth Engine) | $250\text{ m}$, 16-day composite | Quality-filtered vegetation observations, stress-week dip detection, bare-field window | Missing composites stay missing; NDVI is omitted if unavailable |
| **SRTM GL1** | NASA / USGS (`srtm30m` elevation service) | $30\text{ m}$ (1 arc-sec), Static | Elevation, slope, and a low-confidence local-relief indicator | Missing terrain remains unavailable; crop feasibility is withheld |
| **SMAP L4** | NSIDC DAAC (`SPL4SMGP.008`) | $9\text{ km}$, 3-hourly / Daily | Root-zone soil moisture anomaly, dry season planting water | Farmer moisture answer (`dry`, `moist`, `wet`) |
| **GLDAS Noah** | NASA GES DISC (`GLDAS_NOAH025_3H`) | $\sim 25\text{ km}$ ($0.25^\circ$), 3-hourly | Evapotranspiration proxy, gap-free backup time series | POWER radiation / temperature proxy |
| **ISRIC SoilGrids** | ISRIC REST API (v2.0) | $250\text{ m}$, Static | Soil pH, texture fractions, organic carbon estimate | Missing values remain unavailable; farmer soil correction |
| **IMD Gridded** | India Meteorological Dept | $0.25^\circ$, Daily | Ground-truth rain gauge validation against IMERG | IMERG satellite precipitation |

---

## 2. Integration & Cache Behavior

- Set `EE_PROJECT` and configure Google application-default credentials to enable
  Earth Engine MODIS and IMERG extraction. The backend does not run an interactive
  Earth Engine login. Without credentials, POWER remains the rainfall source and
  missing NDVI is reported as a data gap.
- NASA POWER daily and weekly series are cached by 0.5-degree cell. MODIS and IMERG
  data are keyed to the field's point (approximately 250 m for MODIS) so neighboring
  fields do not reuse a coarse climate-cell NDVI series.
- `python scripts/pull_cell.py --lat <latitude> --lon <longitude>` fetches NASA
  POWER data and builds the Parquet climatology cache. Add `--refresh` to refetch
  provider data or `--years` to change the history window.
- SRTM terrain is retrieved through OpenTopoData's `srtm30m` endpoint, which serves
  the 30 m SRTM elevation grid. The flood flag is only a local-relief heuristic and
  is explicitly low-confidence; it is not flood-history or hydrologic modeling.
- SoilGrids pH is scaled from pH×10; soil organic carbon is stored as percent, and
  texture fractions are converted from the API's deci-percent representation.
  Drainage is a low-confidence estimate from soil texture and terrain slope.

## 3. Latency & Temporal Alignment Notes

- **GPM / IMERG Final vs Late:** The Earth Engine `NASA/GPM_L3/IMERG_V07` collection can include provisional observations. This pipeline labels IMERG observations as potentially provisional and falls back to NASA POWER when a weekly coverage threshold is not met; it does not select a separate Final/Late product.
- **Monsoon Cloud Masking:** During the Southwest Monsoon (June–August in Kerala), optical satellite passes (MODIS, Landsat) frequently suffer from dense cloud cover. The pipeline explicitly marks masked weeks as **"No clear image this period"** rather than interpolating values.

## 4. Ground Truth Data Narrowing

1. **Soil Health Cards:** Farmer-supplied soil test results override coarse SoilGrids estimates. The UI displays both: the verified farmer value and the background satellite estimate.
2. **IMD Seasonal Monsoon Outlooks:** Long-range monsoon forecast bulletins issued by IMD are encoded into the 5–8 month water outlook factor ($0.80$ to $1.15$).
3. **KAU Package of Practices:** Agronomic crop parameters (duration, critical watering stages, temperature ranges, nutrient effects) are derived from the Kerala Agricultural University package of practices.
