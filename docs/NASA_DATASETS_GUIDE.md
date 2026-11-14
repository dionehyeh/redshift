# Field Shift NASA Earth Observations & Datasets Guide

This document catalogs every satellite and in-situ dataset utilized by Field Shift, detailing its purpose, access methods, spatial/temporal resolutions, and operational fallbacks.

---

## 1. Datasets Catalog

| Dataset | Provider & Product ID | Spatial / Temporal Resolution | Pipeline Usage | Fallback Strategy |
|---|---|---|---|---|
| **NASA POWER** | Langley Research Center (`AG` Community) | $\sim 50\text{ km}$ ($0.5^\circ$), Daily | 20-year climatological normals, thermal limits, frost risk | Cached grid cell Parquet file |
| **GPM / IMERG** | NASA GES DISC (`GPM_3IMERGDF` / `DL`) | $\sim 10\text{ km}$ ($0.1^\circ$), Daily | Weekly precipitation sums, dry spell duration, waterlogging risk | NASA POWER rainfall with coarse tag |
| **MODIS NDVI** | LP DAAC (`MOD13Q1.061`) | $250\text{ m}$, 16-day composite | Crop greenness curve, stress-week dip detection, bare-field window | GLDAS soil moisture signal / "No clear image" flag |
| **SRTM GL1** | NASA / USGS (`SRTMGL1_003`) | $30\text{ m}$ (1 arc-sec), Static | Elevation, slope %, low-lying flood-prone classification | Static DEM fixture |
| **SMAP L4** | NSIDC DAAC (`SPL4SMGP.008`) | $9\text{ km}$, 3-hourly / Daily | Root-zone soil moisture anomaly, dry season planting water | Farmer moisture answer (`dry`, `moist`, `wet`) |
| **GLDAS Noah** | NASA GES DISC (`GLDAS_NOAH025_3H`) | $\sim 25\text{ km}$ ($0.25^\circ$), 3-hourly | Evapotranspiration proxy, gap-free backup time series | POWER radiation / temperature proxy |
| **ISRIC SoilGrids** | ISRIC REST API (v2.0) | $250\text{ m}$, Static | Soil pH, clay/sand texture, organic carbon estimate | District Soil Health Card average / Farmer override |
| **IMD Gridded** | India Meteorological Dept | $0.25^\circ$, Daily | Ground-truth rain gauge validation against IMERG | IMERG satellite precipitation |

---

## 2. Latency & Temporal Alignment Notes

- **GPM / IMERG Final vs Late:** The Final IMERG run (`GPM_3IMERGDF`) has a latency of $\sim 3.5\text{ months}$. For the active cropping season, the pipeline fetches the Late run (`GPM_3IMERGDL`, $\sim 14\text{ hours}$ latency) and tags the data as "Provisional".
- **Monsoon Cloud Masking:** During the Southwest Monsoon (June–August in Kerala), optical satellite passes (MODIS, Landsat) frequently suffer from dense cloud cover. The pipeline explicitly marks masked weeks as **"No clear image this period"** rather than interpolating values.

---

## 3. Ground Truth Data Narrowing

1. **Soil Health Cards:** Farmer-supplied soil test results override coarse SoilGrids estimates. The UI displays both: the verified farmer value and the background satellite estimate.
2. **IMD Seasonal Monsoon Outlooks:** Long-range monsoon forecast bulletins issued by IMD are encoded into the 5–8 month water outlook factor ($0.80$ to $1.15$).
3. **KAU Package of Practices:** Agronomic crop parameters (duration, critical watering stages, temperature ranges, nutrient effects) are derived from the Kerala Agricultural University package of practices.
