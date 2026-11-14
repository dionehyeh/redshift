import numpy as np
import pandas as pd
from app.analysis.core import (
    clean_daily,
    to_weekly,
    weekly_normals,
    runs,
    rain_deficit_runs,
    stage_calendar,
    stage_of,
    water_outlook,
    stored_soil_water,
    lowest,
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
