"""Field Shift data analysis (Section 19).
Pure mathematical functions using pandas and numpy only: no network and no database side effects.
"""
import numpy as np
import pandas as pd

MIN_YEARS = 10
STD_FLOOR = {"rain_mm": 5.0, "t2m": 0.3, "tmax": 0.3, "ndvi": 0.03}
STAGE_WEIGHT = {
    "establishment": 1.2,
    "vegetative": 1.0,
    "flowering": 1.5,
    "filling": 1.3,
    "maturity": 0.7,
}

# ---------- 19.4 Data Cleaning ----------
def clean_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Clean daily observations: convert -999/-9999 missing flags to NaN and clip negative rain."""
    df = df.replace(-999, np.nan).replace(-9999, np.nan)
    if "rain_mm" in df:
        df["rain_mm"] = df["rain_mm"].clip(lower=0)
    return df.sort_index()

# ---------- 19.5 Weekly Aggregation ----------
def to_weekly(
    df: pd.DataFrame,
    sum_cols: tuple[str, ...] = ("rain_mm",),
    mean_cols: tuple[str, ...] = ("t2m", "tmax", "ndvi", "soil_moist"),
) -> pd.DataFrame:
    """Aggregate daily to ISO calendar weeks. Week 53 is folded into week 52."""
    df = df.copy()
    iso = df.index.isocalendar()
    df["year"] = iso.year.astype(int)
    df["week"] = iso.week.astype(int).clip(upper=52)
    sc = [c for c in sum_cols if c in df]
    mc = [c for c in mean_cols if c in df]
    g = df.groupby(["year", "week"])
    days = g.size()
    out = pd.concat([g[sc].sum(min_count=1).mul(7.0 / days, axis=0), g[mc].mean()], axis=1)
    out["days"] = days
    return out

# ---------- 19.6 Normals ----------
def weekly_normals(
    wk: pd.DataFrame,
    cols: list[str],
    year_from: int | None = None,
    year_to: int | None = None,
) -> pd.DataFrame:
    """Compute 52-week mean, std and count per week. Thin weeks are filled circularly."""
    yrs = wk.index.get_level_values("year")
    sel = wk[(yrs >= (year_from or yrs.min())) & (yrs <= (year_to or yrs.max()))]
    g = sel.groupby(level="week")[cols].agg(["mean", "std", "count"])
    g = g.reindex(range(1, 53))
    for c in cols:
        g.loc[g[(c, "count")] < MIN_YEARS, [(c, "mean"), (c, "std")]] = np.nan
        for stat in ("mean", "std"):
            s = g[(c, stat)]
            ext = pd.concat([s, s, s]).interpolate(limit_direction="both")
            g[(c, stat)] = ext.iloc[52:104].values
    return g

def normals_arrays(g: pd.DataFrame, cols: list[str]) -> dict[str, list[float]]:
    return {c: [float(x) for x in g[(c, "mean")].values] for c in cols}

# ---------- 19.7 Anomalies ----------
def anomalies(wk_year: pd.DataFrame, g: pd.DataFrame, col: str) -> pd.DataFrame:
    """Calculate z-score and percent deviation for one season's weekly frame."""
    w = wk_year.index.get_level_values("week") if isinstance(wk_year.index, pd.MultiIndex) else wk_year.index
    mean = g[(col, "mean")].reindex(w).values
    std = np.maximum(g[(col, "std")].reindex(w).values, STD_FLOOR.get(col, 0.1))
    val = wk_year[col].values
    return pd.DataFrame(
        {
            "z": (val - mean) / std,
            "pct": (val / np.where(mean == 0, np.nan, mean) - 1) * 100,
            "value": val,
            "normal": mean,
        },
        index=wk_year.index,
    )

# ---------- 19.8 / 19.9 Run Detection ----------
def runs(mask: np.ndarray | list[bool], min_len: int = 2) -> list[tuple[int, int]]:
    """Identify continuous True intervals of at least min_len as inclusive (start, end) tuples."""
    out, start = [], None
    for i, m in enumerate(list(mask) + [False]):
        if m and start is None:
            start = i
        if not m and start is not None:
            if i - start >= min_len:
                out.append((start, i - 1))
            start = None
    return out

def rain_deficit_runs(z: np.ndarray | list[float], thr: float = -1.0, min_len: int = 2) -> list[tuple[int, int]]:
    return runs(np.asarray(z) < thr, min_len)

def heat_runs(tmax: np.ndarray | list[float], limit_c: float, min_len: int = 2) -> list[tuple[int, int]]:
    return runs(np.asarray(tmax) > limit_c, min_len)

def ndvi_dip_runs(z: np.ndarray | list[float], thr: float = -1.0, min_len: int = 2) -> list[tuple[int, int]]:
    return runs(np.asarray(z) < thr, min_len)

def cloud_gap_runs(ndvi: np.ndarray | list[float], min_len: int = 2) -> list[tuple[int, int]]:
    return runs(np.isnan(np.asarray(ndvi, dtype=float)), min_len)

def bare_runs(ndvi: np.ndarray | list[float], thr: float = 0.25, min_weeks: int = 8) -> list[tuple[int, int]]:
    return runs(np.asarray(ndvi, dtype=float) < thr, min_weeks)

# ---------- 19.10 Crop Stage Calendar ----------
def stage_calendar(duration_days: int, flower_frac: tuple[float, float]) -> list[tuple[str, float, float]]:
    n = duration_days / 7.0
    a, b = flower_frac
    return [
        ("establishment", 0, 0.2 * n),
        ("vegetative", 0.2 * n, a * n),
        ("flowering", a * n, b * n),
        ("filling", b * n, 0.9 * n),
        ("maturity", 0.9 * n, n),
    ]

def stage_of(week_since_planting: float, cal: list[tuple[str, float, float]]) -> str:
    for name, lo, hi in cal:
        if lo <= week_since_planting < hi:
            return name
    return cal[-1][0]

# ---------- 19.11 Findings Synthesis ----------
def build_findings(
    season_weeks: list[int],
    rain_z: list[float],
    rain_pct: list[float],
    tmax: list[float],
    ndvi: list[float],
    ndvi_z: list[float],
    crop: dict,
    source_meta: dict,
) -> tuple[list[dict], list[str]]:
    cal = stage_calendar(crop["duration_days"], crop["flower_frac"])
    findings = []

    def add(kind: str, run: tuple[int, int], key: str, sev_base: float, extra: dict):
        s, e = run
        stage = stage_of(s, cal)
        meta = source_meta.get(kind, {"source": "Satellite", "resolution": "Regional", "confidence": "medium"})
        findings.append(
            {
                "kind": kind,
                "weeks": [s + 1, e + 1],
                "crop_stage": stage,
                "message_key": key,
                "severity": round(sev_base * (e - s + 1) * STAGE_WEIGHT[stage], 2),
                **extra,
                **meta,
            }
        )

    for r in rain_deficit_runs(rain_z):
        sub_pct = np.asarray(rain_pct)[r[0] : r[1] + 1]
        add(
            "rain_deficit",
            r,
            "finding.rain_deficit",
            float(abs(np.mean(np.asarray(rain_z)[r[0] : r[1] + 1]))),
            {"deviation": f"{np.mean(sub_pct):.0f}%"},
        )
    for r in heat_runs(tmax, crop["t_flower_max"]):
        sub_t = np.asarray(tmax)[r[0] : r[1] + 1]
        diff = float(np.mean(sub_t) - crop["t_flower_max"])
        add(
            "heat",
            r,
            "finding.heat",
            diff,
            {"deviation": f"+{diff:.1f} C above limit"},
        )
    for r in ndvi_dip_runs(ndvi_z):
        add(
            "ndvi_dip",
            r,
            "finding.ndvi_dip",
            float(abs(np.nanmean(np.asarray(ndvi_z)[r[0] : r[1] + 1]))),
            {"deviation": "greenness below normal"},
        )

    findings.sort(key=lambda f: -f["severity"])
    gaps = [f"No clear image in weeks {a + 1} to {b + 1} (cloud cover)" for a, b in cloud_gap_runs(ndvi)]
    return findings, gaps

# ---------- 19.12 Likely-Cause Synthesis ----------
CAUSE_MAP = {
    "rain_deficit": "water_stress",
    "heat": "heat_stress",
    "ndvi_dip": "unknown_vegetation_stress",
}

def likely_causes(findings: list[dict], farmer_cause: str | None = None) -> dict:
    suspected = [
        {
            "cause": CAUSE_MAP.get(f["kind"], "unspecified_stress"),
            "from_finding": f["kind"],
            "weeks": f["weeks"],
            "stage": f["crop_stage"],
        }
        for f in findings[:3]
    ]
    return {
        "suspected": suspected,
        "farmer_cause": farmer_cause,
        "not_assessable": ["pests and disease", "nutrient deficiency", "management and labour"],
    }

# ---------- 19.13 Seasonal Water Outlook ----------
def water_outlook(
    normal_rain: list[float],
    start_week: int,
    n_weeks: int,
    imd_factor_range: tuple[float, float] | None = None,
    season_to_date_pct: float | None = None,
) -> dict:
    idx = [(start_week - 1 + i) % 52 for i in range(n_weeks)]
    base = float(sum(normal_rain[i] for i in idx))
    lo, hi = imd_factor_range or (0.85, 1.15)
    if season_to_date_pct is not None and not imd_factor_range:
        shift = max(-0.15, min(0.15, season_to_date_pct / 100.0 * 0.5))
        lo += shift
        hi += shift
    mid = (lo + hi) / 2
    label = "below normal" if mid < 0.9 else "above normal" if mid > 1.1 else "near normal"
    return {
        "low_mm": round(base * lo),
        "mid_mm": round(base * mid),
        "high_mm": round(base * hi),
        "factor": round(mid, 2),
        "label": label,
        "confidence": "medium" if imd_factor_range else "low",
    }

# ---------- 19.15 Terrain & Flood ----------
def slope_percent(dem: np.ndarray, cell_m: float = 30.0) -> float:
    gy, gx = np.gradient(dem.astype(float), cell_m)
    s = np.hypot(gx, gy)
    mid_y, mid_x = dem.shape[0] // 2, dem.shape[1] // 2
    return float(np.nanmean(s[mid_y - 1 : mid_y + 2, mid_x - 1 : mid_x + 2]) * 100)

def relative_elevation(dem: np.ndarray) -> float:
    c = dem[dem.shape[0] // 2, dem.shape[1] // 2]
    return float(c - np.nanpercentile(dem, 10))

def flood_prone(elev_m: float, rel_elev_m: float, slope_pct: float) -> bool:
    return bool(elev_m <= 5 or (rel_elev_m <= 2 and slope_pct <= 2))

def drainage_class(clay_pct: float, flood: bool, slope_pct: float) -> str:
    if flood or clay_pct >= 40:
        return "poor"
    if clay_pct >= 25 and slope_pct < 5:
        return "moderate"
    return "good"

# ---------- 19.18 Stored Soil Water at Planting ----------
ANSWER_FRACTION = {"dry": 0.0, "moist": 0.5, "wet": 1.0}

def stored_soil_water(
    answer: str | None = None,
    sm_vol: float | None = None,
    cap_mm: float = 150.0,
    wilting: float = 0.10,
    field_cap: float = 0.35,
) -> tuple[float, str, str]:
    if answer in ANSWER_FRACTION:
        return round(cap_mm * ANSWER_FRACTION[answer], 1), "high", "farmer answer"
    if sm_vol is not None and not np.isnan(sm_vol):
        f = min(1.0, max(0.0, (sm_vol - wilting) / (field_cap - wilting)))
        return round(cap_mm * f, 1), "medium", "satellite normal soil moisture"
    return round(cap_mm * 0.3, 1), "low", "default estimate (30% capacity)"

# ---------- 19.17 Confidence Ranking ----------
RANK = {"low": 0, "medium": 1, "high": 2}

def water_confidence(n_years: int, gauge_rel_diff: float | None = None) -> str:
    if gauge_rel_diff is not None and abs(gauge_rel_diff) <= 0.2 and n_years >= 15:
        return "high"
    return "medium" if n_years >= MIN_YEARS else "low"

def lowest(*levels: str) -> str:
    return min(levels, key=lambda l: RANK.get(l.lower(), 0))
