from datetime import date

import pandas as pd

from app.services.analysis_service import analyze_weekly_data


def test_analyze_weekly_data_uses_observations_and_historical_normals():
    rows = []
    for year in range(2010, 2022):
        for week in range(1, 53):
            rain = 20.0
            tmax = 30.0
            if year == 2020 and week in (10, 11):
                rain = 0.0
            if year == 2020 and week in (18, 19):
                tmax = 40.0
            rows.append((year, week, rain, 27.0, tmax))
    weekly = pd.DataFrame(
        rows,
        columns=["year", "week", "rain_mm", "tmean", "tmax"],
    ).set_index(["year", "week"])
    crop = {
        "duration_days": 140,
        "flower_frac": (0.25, 0.65),
        "t_flower_max": 35.0,
    }

    findings, gaps, comparison = analyze_weekly_data(
        weekly,
        date(2020, 3, 2),
        date(2020, 5, 25),
        crop,
    )

    rain = next(finding for finding in findings if finding["kind"] == "rain_deficit")
    heat = next(finding for finding in findings if finding["kind"] == "heat")
    assert rain["weeks"] == [10, 11]
    assert heat["weeks"] == [18, 19]
    assert rain["source"] == "NASA POWER"
    assert comparison == "2010-2021 (12-year climatology)"
    assert "NDVI observations are unavailable for this season" in gaps
    assert not any(finding["kind"] in {"cloud_gap", "ndvi_dip", "bare_field"} for finding in findings)
