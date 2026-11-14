import numpy as np
import pandas as pd
from app.analysis.core import (
    clean_daily,
    to_weekly,
    weekly_normals,
    anomalies,
    runs,
    rain_deficit_runs,
    stage_calendar,
    stage_of,
    build_findings,
    water_outlook,
    stored_soil_water,
    lowest,
    slope_percent,
    relative_elevation,
)

def test_clean_daily_handles_missing():
    df = pd.DataFrame({"rain_mm": [-999, 15.0, -10.0], "t2m": [-9999, 28.5, 30.0]})
    cleaned = clean_daily(df)
    assert np.isnan(cleaned["rain_mm"].iloc[0])
    assert cleaned["rain_mm"].iloc[1] == 15.0
    assert cleaned["rain_mm"].iloc[2] == 0.0  # clipped negative
    assert np.isnan(cleaned["t2m"].iloc[0])

def test_to_weekly_clips_week_53():
    # Construct 10-day range spanning new year
    dates = pd.date_range("2020-12-25", periods=10, freq="D")
    df = pd.DataFrame({"rain_mm": [5.0] * 10, "t2m": [25.0] * 10}, index=dates)
    wk = to_weekly(df)
    weeks = wk.index.get_level_values("week")
    assert all(w <= 52 for w in weeks)

def test_to_weekly_rain_is_prorated_by_valid_observations():
    dates = pd.date_range("2024-01-01", periods=7, freq="D")
    df = pd.DataFrame({"rain_mm": [10.0, np.nan, 10.0, np.nan, np.nan, np.nan, np.nan]}, index=dates)
    weekly = to_weekly(df)
    assert weekly["rain_mm"].iloc[0] == 70.0
    assert weekly["days"].iloc[0] == 7

def test_weekly_normals_obey_minimum_year_count_and_fill_circularly():
    rows = []
    for year in range(2000, 2012):
        for week in range(1, 53):
            rows.append((year, week, float(week)))
    frame = pd.DataFrame(rows, columns=["year", "week", "rain_mm"]).set_index(["year", "week"])
    normals = weekly_normals(frame, ["rain_mm"])
    assert normals.loc[1, ("rain_mm", "count")] == 12
    assert normals.loc[1, ("rain_mm", "mean")] == 1
    assert normals.loc[1, ("rain_mm", "std")] == 0

    thin = frame.loc[(slice(2000, 2008), slice(None)), :]
    thin_normals = weekly_normals(thin, ["rain_mm"])
    assert not np.isnan(thin_normals.loc[10, ("rain_mm", "count")])
    assert np.isnan(thin_normals.loc[10, ("rain_mm", "mean")])

def test_anomalies_apply_minimum_standard_deviation_floor():
    index = pd.MultiIndex.from_tuples([(2024, 1)], names=["year", "week"])
    week = pd.DataFrame({"rain_mm": [15.0]}, index=index)
    normal_index = pd.RangeIndex(1, 53)
    normals = pd.DataFrame(
        {(col, stat): [value] * 52 for col, mean, std in [("rain_mm", 10.0, 0.0)]
         for stat, value in [("mean", mean), ("std", std)]},
        index=normal_index,
    )
    result = anomalies(week, normals, "rain_mm")
    assert result["z"].iloc[0] == 1.0

def test_runs_detection():
    mask = [False, True, True, True, False, True, True]
    detected = runs(mask, min_len=2)
    assert detected == [(1, 3), (5, 6)]

def test_stage_calendar_and_stage_of():
    cal = stage_calendar(duration_days=70, flower_frac=(0.4, 0.6))
    assert stage_of(1.0, cal) == "establishment"
    assert stage_of(5.0, cal) == "flowering"
    assert stage_of(9.5, cal) == "maturity"

def test_stored_soil_water_hierarchy():
    # Farmer answer takes priority
    val, conf, _ = stored_soil_water(answer="wet")
    assert val == 150.0
    assert conf == "high"

    # Satellite fallback
    val_sat, conf_sat, _ = stored_soil_water(answer=None, sm_vol=0.25)
    assert conf_sat == "medium"

    # Default fallback
    val_def, conf_def, _ = stored_soil_water(answer=None, sm_vol=None)
    assert conf_def == "low"

def test_lowest_confidence():
    assert lowest("high", "medium", "low") == "low"
    assert lowest("high", "high", "medium") == "medium"

def test_findings_include_nan_gaps_and_bare_field_runs_with_calendar_weeks():
    crop = {
        "duration_days": 140,
        "flower_frac": (0.4, 0.6),
        "t_flower_max": 35,
    }
    weeks = list(range(10, 22))
    ndvi = [0.2] * 8 + [np.nan, np.nan] + [0.4, 0.5]
    findings, gaps = build_findings(
        weeks,
        [0.0] * 12,
        [0.0] * 12,
        [30.0] * 12,
        ndvi,
        [0.0] * 12,
        crop,
        {"cloud_gap": {"source": "MODIS", "resolution": "250 m", "confidence": "medium"}},
    )
    bare = next(f for f in findings if f["kind"] == "bare_field")
    gap = next(f for f in findings if f["kind"] == "cloud_gap")
    assert bare["weeks"] == [10, 17]
    assert gap["weeks"] == [18, 19]
    assert gaps == ["No clear image in weeks 18 to 19 (cloud cover)"]

def test_terrain_calculations_validate_dem_and_return_expected_values():
    dem = np.tile(np.arange(5, dtype=float), (5, 1))
    assert round(slope_percent(dem), 6) == round(100 / 30, 6)
    assert relative_elevation(dem) == 2.0
    with np.testing.assert_raises(ValueError):
        slope_percent(np.ones((2, 2)))
