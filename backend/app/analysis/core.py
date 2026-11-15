"""Field Shift data analysis (Section 19).
Pure mathematical functions using pandas and numpy only: no network and no database side effects.
"""
import numpy as np
import pandas as pd

MIN_YEARS = 10
STD_FLOOR = {"rain_mm": 5.0, "t2m": 0.3, "tmean": 0.3, "tmax": 0.3, "ndvi": 0.03}
STAGE_WEIGHT = {
    "establishment": 1.2,
    "vegetative": 1.0,
    "flowering": 1.5,
    "filling": 1.3,
    "maturity": 0.7,
}

# ---------- 19.4 Data Cleaning ----------
def clean_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Clean provider missing flags, scale raw MODIS NDVI, and clip negative rain."""
    df = df.replace(-999, np.nan).replace(-9999, np.nan)
    if "rain_mm" in df:
        df["rain_mm"] = df["rain_mm"].clip(lower=0)
    if "ndvi" in df:
        df["ndvi"] = df["ndvi"].replace(-3000, np.nan)
        if df["ndvi"].abs().max(skipna=True) > 1:
            df["ndvi"] = df["ndvi"] * 0.0001
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
    out = pd.DataFrame(index=g.size().index)
    for col in sc:
        valid_days = g[col].count()
        totals = g[col].sum(min_count=1)
        out[col] = totals.mul(7.0 / valid_days.where(valid_days > 0))
    for col in mc:
        out[col] = g[col].mean()
    out["days"] = g.size()
    return out

# ---------- 19.6 Normals ----------
def weekly_normals(
    wk: pd.DataFrame,
    cols: list[str],
    year_from: int | None = None,
    year_to: int | None = None,
) -> pd.DataFrame:
    """Compute 52-week mean, std and count per week. Thin weeks are filled circularly."""
    if not isinstance(wk.index, pd.MultiIndex) or not {"year", "week"}.issubset(wk.index.names):
        raise ValueError("weekly data must have a MultiIndex named 'year' and 'week'")
    missing_cols = set(cols).difference(wk.columns)
    if missing_cols:
        raise ValueError(f"weekly data is missing columns: {', '.join(sorted(missing_cols))}")
    if wk.empty:
        raise ValueError("weekly data cannot be empty")
    yrs = wk.index.get_level_values("year")
    first_year = int(yrs.min()) if year_from is None else year_from
    last_year = int(yrs.max()) if year_to is None else year_to
    if first_year > last_year:
        raise ValueError("year_from must not be after year_to")
    sel = wk[(yrs >= first_year) & (yrs <= last_year)]
    g = sel.groupby(level="week")[cols].agg(["mean", "std", "count"])
    g = g.reindex(range(1, 53))
    for c in cols:
        g.loc[g[(c, "count")] < MIN_YEARS, [(c, "mean"), (c, "std")]] = np.nan
        for stat in ("mean", "std"):
            s = g[(c, stat)]
            if s.notna().any():
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
    with np.errstate(divide="ignore", invalid="ignore"):
        pct = (val / np.where(mean == 0, np.nan, mean) - 1) * 100
    return pd.DataFrame(
        {
            "z": (val - mean) / std,
            "pct": pct,
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
    if duration_days <= 0:
        raise ValueError("duration_days must be positive")
    n = duration_days / 7.0
    a, b = flower_frac
    if not (0 <= a < b <= 1):
        raise ValueError("flower_frac must satisfy 0 <= start < end <= 1")
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
    ndvi: list[float | None] | None,
    ndvi_z: list[float | None] | None,
    crop: dict,
    source_meta: dict,
    ndvi_data_available: bool = True,
) -> tuple[list[dict], list[str]]:
    cal = stage_calendar(crop["duration_days"], crop["flower_frac"])
    findings = []
    arrays = {
        "rain_z": np.asarray(rain_z, dtype=float),
        "rain_pct": np.asarray(rain_pct, dtype=float),
        "tmax": np.asarray(tmax, dtype=float),
    }
    if (ndvi is None) != (ndvi_z is None):
        raise ValueError("NDVI values and anomalies must either both be provided or omitted")
    ndvi_available = ndvi is not None
    if ndvi_available:
        arrays["ndvi"] = np.asarray(ndvi, dtype=float)
        arrays["ndvi_z"] = np.asarray(ndvi_z, dtype=float)
    lengths = {len(values) for values in arrays.values()}
    if len(lengths) != 1 or (season_weeks and len(season_weeks) != len(rain_z)):
        raise ValueError("season data arrays and week labels must have matching lengths")

    def week_label(index: int) -> int:
        return season_weeks[index] if season_weeks else index + 1

    def add(kind: str, run: tuple[int, int], key: str, sev_base: float, extra: dict):
        s, e = run
        stage = stage_of(s, cal)
        meta = source_meta.get(kind, {"source": "Satellite", "resolution": "Regional", "confidence": "medium"})
        findings.append(
            {
                "kind": kind,
                "weeks": [week_label(s), week_label(e)],
                "crop_stage": stage,
                "message_key": key,
                "severity": round(sev_base * (e - s + 1) * STAGE_WEIGHT[stage], 2),
                **extra,
                **meta,
            }
        )

    for r in rain_deficit_runs(np.where(np.isfinite(arrays["rain_z"]), arrays["rain_z"], np.inf)):
        sub_pct = arrays["rain_pct"][r[0] : r[1] + 1]
        add(
            "rain_deficit",
            r,
            "finding.rain_deficit",
            float(abs(np.mean(arrays["rain_z"][r[0] : r[1] + 1]))),
            {
                "deviation": f"{np.mean(sub_pct):.0f}%",
                "deviation_value": float(np.nanmean(sub_pct)),
                "unit": "%",
            },
        )
    flowering = next(stage for stage in cal if stage[0] == "flowering")
    safe_tmax = np.where(
        np.isfinite(arrays["tmax"])
        & np.asarray(
            [flowering[1] <= i < flowering[2] for i in range(len(arrays["tmax"]))]
        ),
        arrays["tmax"],
        -np.inf,
    )
    for r in heat_runs(safe_tmax, crop["t_flower_max"]):
        sub_t = arrays["tmax"][r[0] : r[1] + 1]
        diff = float(np.mean(sub_t) - crop["t_flower_max"])
        add(
            "heat",
            r,
            "finding.heat",
            diff,
            {"deviation": f"+{diff:.1f} C above limit"},
        )
    if ndvi_available:
        safe_ndvi_z = np.where(np.isfinite(arrays["ndvi_z"]), arrays["ndvi_z"], np.inf)
        for r in ndvi_dip_runs(safe_ndvi_z):
            add(
                "ndvi_dip",
                r,
                "finding.ndvi_dip",
                float(abs(np.nanmean(arrays["ndvi_z"][r[0] : r[1] + 1]))),
                {"deviation": "greenness below normal"},
            )

        for r in cloud_gap_runs(arrays["ndvi"]):
            add(
                "cloud_gap",
                r,
                "finding.cloud_gap",
                0.0,
                {"deviation": "no clear NDVI observation", "data_gap": True},
            )
        for r in bare_runs(arrays["ndvi"]):
            add(
                "bare_field",
                r,
                "finding.bare_field",
                float(max(0.0, 0.25 - np.nanmean(arrays["ndvi"][r[0] : r[1] + 1]))),
                {"deviation": "low vegetation cover", "data_gap": False},
            )

    findings.sort(key=lambda f: -f["severity"])
    gaps = [
        f"No clear image in weeks {week_label(a)} to {week_label(b)} (cloud cover)"
        for a, b in cloud_gap_runs(arrays["ndvi"])
    ] if ndvi_available else ["NDVI observations are unavailable for this season"]
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
            "cause": CAUSE_MAP[f["kind"]],
            "from_finding": f["kind"],
            "weeks": f["weeks"],
            "stage": f["crop_stage"],
        }
        for f in findings
        if f.get("kind") in CAUSE_MAP
    ]
    suspected = suspected[:3]
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
    if len(normal_rain) != 52:
        raise ValueError("normal_rain must contain exactly 52 weekly values")
    if not 1 <= start_week <= 52 or n_weeks <= 0:
        raise ValueError("start_week must be 1-52 and n_weeks must be positive")
    if not np.isfinite(normal_rain).all() or any(value < 0 for value in normal_rain):
        raise ValueError("normal_rain values must be finite and non-negative")
    if imd_factor_range is not None:
        lo, hi = imd_factor_range
        if not np.isfinite([lo, hi]).all() or lo < 0 or hi < lo:
            raise ValueError("imd_factor_range must contain ordered non-negative values")
    if season_to_date_pct is not None and not np.isfinite(season_to_date_pct):
        raise ValueError("season_to_date_pct must be finite")
    idx = [(start_week - 1 + i) % 52 for i in range(n_weeks)]
    selected_rain = np.asarray([normal_rain[i] for i in idx], dtype=float)
    if not np.isfinite(selected_rain).all():
        raise ValueError("selected rainfall normals must be finite")
    base = float(selected_rain.sum())
    lo, hi = imd_factor_range or (0.85, 1.15)
    if not np.isfinite([lo, hi]).all() or lo < 0 or hi < lo:
        raise ValueError("IMD outlook factors must be finite, non-negative, and ordered")
    if season_to_date_pct is not None and not imd_factor_range:
        if not np.isfinite(season_to_date_pct):
            raise ValueError("season_to_date_pct must be finite")
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
    if dem.ndim != 2 or min(dem.shape) < 3:
        raise ValueError("DEM must be a two-dimensional grid at least 3 by 3")
    if not np.isfinite(cell_m) or cell_m <= 0:
        raise ValueError("cell_m must be a positive finite distance")
    gy, gx = np.gradient(dem.astype(float), cell_m)
    s = np.hypot(gx, gy)
    mid_y, mid_x = dem.shape[0] // 2, dem.shape[1] // 2
    center_slope = s[mid_y - 1 : mid_y + 2, mid_x - 1 : mid_x + 2]
    if not np.isfinite(center_slope).any():
        raise ValueError("DEM has no valid elevations around its center")
    return float(np.nanmean(center_slope) * 100)

def relative_elevation(dem: np.ndarray) -> float:
    if dem.ndim != 2 or dem.size == 0:
        raise ValueError("DEM must be a non-empty two-dimensional grid")
    if not np.isfinite(dem).any():
        raise ValueError("DEM has no valid elevations")
    c = dem[dem.shape[0] // 2, dem.shape[1] // 2]
    if not np.isfinite(c):
        raise ValueError("DEM center elevation is missing")
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
    if not np.isfinite(cap_mm) or cap_mm < 0:
        raise ValueError("cap_mm must be a non-negative finite value")
    if not np.isfinite(wilting) or not np.isfinite(field_cap) or field_cap <= wilting:
        raise ValueError("field_cap must be greater than a finite wilting point")
    normalized_answer = answer.lower() if isinstance(answer, str) else None
    if normalized_answer in ANSWER_FRACTION:
        return round(cap_mm * ANSWER_FRACTION[normalized_answer], 1), "high", "farmer answer"
    if sm_vol is not None and not np.isfinite(sm_vol):
        raise ValueError("sm_vol must be finite when provided")
    if sm_vol is not None:
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
