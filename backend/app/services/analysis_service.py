"""Season analysis orchestration using cached and observed climate data."""

import logging

import numpy as np
import pandas as pd

from app.analysis.core import (
    anomalies,
    build_findings,
    likely_causes,
    to_weekly,
    weekly_normals,
)
from app.db import get_db
from app.engine.scoring import load_crops
from app.jobs import complete_job, fail_job, update_job_step
from app.services.climate_service import grid_cell_id, load_cell_daily, load_cell_weekly

logger = logging.getLogger(__name__)


def _column_values(frame: pd.DataFrame, column: str, length: int) -> np.ndarray:
    if column not in frame.columns:
        return np.full(length, np.nan)
    return frame[column].to_numpy(dtype=float)


def analyze_season_task(job_id: str, season_id: int) -> None:
    try:
        update_job_step(job_id, "loading_season", 20)
        with get_db() as conn:
            row = conn.execute(
                """SELECT s.*, c.name AS crop_name, f.lat, f.lon, f.climate_cell_id
                   FROM seasons s
                   JOIN fields f ON f.id = s.field_id
                   LEFT JOIN crops c ON c.id = s.crop_id
                   WHERE s.id = ?""",
                (season_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Season {season_id} does not exist")
            season = dict(row)

        if not season.get("start_date"):
            raise ValueError(f"Season {season_id} has no start date")
        crop_name = season.get("crop_name") or "paddy"
        crops = {crop["name"]: crop for crop in load_crops()}
        if crop_name not in crops:
            raise ValueError(f"Crop {crop_name!r} is not in the analysis catalog")
        crop = crops[crop_name]

        start = pd.Timestamp(season["start_date"]).normalize()
        end = (
            pd.Timestamp(season["end_date"]).normalize()
            if season.get("end_date")
            else start + pd.Timedelta(days=crop["duration_days"] - 1)
        )
        if end < start:
            raise ValueError("Season end date must not precede its start date")

        cell_id = season.get("climate_cell_id") or grid_cell_id(
            float(season["lat"]), float(season["lon"])
        )
        daily = load_cell_daily(cell_id)
        season_daily = daily.loc[start:end]
        if season_daily.empty:
            raise ValueError(
                f"No cached NASA POWER observations are available for season {season_id}"
            )

        update_job_step(job_id, "calculating_anomalies", 50)
        history_weekly = load_cell_weekly(cell_id)
        available_columns = [
            column for column in ("rain_mm", "tmean", "tmax") if column in history_weekly
        ]
        if "ndvi" in history_weekly:
            available_columns.append("ndvi")
        if not available_columns:
            raise ValueError(f"No supported climate observations are available for {cell_id}")
        normals = weekly_normals(history_weekly, available_columns)

        season_weekly = to_weekly(season_daily)
        season_length = len(season_weekly)
        season_weeks = list(range(1, season_length + 1))
        rain_anomalies = (
            anomalies(season_weekly, normals, "rain_mm")
            if "rain_mm" in available_columns
            else pd.DataFrame(index=season_weekly.index)
        )
        rain_z = _column_values(rain_anomalies, "z", season_length)
        rain_pct = _column_values(rain_anomalies, "pct", season_length)
        tmax = _column_values(season_weekly, "tmax", season_length)

        ndvi_series = (
            history_weekly["ndvi"].reindex(season_weekly.index)
            if "ndvi" in available_columns
            else pd.Series(np.nan, index=season_weekly.index)
        )
        has_ndvi = bool(ndvi_series.notna().any())
        ndvi = ndvi_series.to_numpy(dtype=float)
        ndvi_normals = (
            anomalies(
                pd.DataFrame({"ndvi": ndvi}, index=season_weekly.index),
                normals,
                "ndvi",
            )["z"].to_numpy(dtype=float)
            if has_ndvi
            else np.full(season_length, np.nan)
        )
        ndvi_z = ndvi_normals
        source_meta = {
            "rain_deficit": {
                "source": "NASA POWER precipitation",
                "resolution": "~50 km (coarse fallback)",
                "confidence": "medium",
            },
            "heat": {
                "source": "NASA POWER",
                "resolution": "~50 km",
                "confidence": "high",
            },
        }
        if has_ndvi:
            source_meta["ndvi_dip"] = {
                "source": "MODIS vegetation index",
                "resolution": "~250 m",
                "confidence": "medium",
            }
            source_meta["cloud_gap"] = source_meta["ndvi_dip"]
            source_meta["bare_field"] = source_meta["ndvi_dip"]

        update_job_step(job_id, "synthesizing_stress_flags", 80)
        findings, gaps = build_findings(
            season_weeks,
            rain_z.tolist(),
            rain_pct.tolist(),
            tmax.tolist(),
            ndvi.tolist(),
            ndvi_z.tolist(),
            crop,
            source_meta,
            ndvi_data_available=bool(has_ndvi),
        )
        causes_info = likely_causes(findings, season.get("suspected_cause"))
        with get_db() as conn:
            conn.execute("DELETE FROM findings WHERE season_id = ?", (season_id,))
            for finding in findings:
                deviation = finding.get("deviation_value")
                text_plain = (
                    f"{finding['kind'].replace('_', ' ').capitalize()} "
                    f"detected in weeks {finding['weeks'][0]} to {finding['weeks'][1]}: "
                    f"{finding.get('deviation', 'threshold exceeded')}."
                )
                conn.execute(
                    """INSERT INTO findings (
                           season_id, kind, week_from, week_to, deviation, unit,
                           crop_stage, severity, confidence, source, resolution,
                           text_plain, explainer_key
                       )
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        season_id,
                        finding["kind"],
                        finding["weeks"][0],
                        finding["weeks"][1],
                        deviation,
                        finding.get("unit"),
                        finding["crop_stage"],
                        str(finding["severity"]),
                        finding["confidence"],
                        finding["source"],
                        finding["resolution"],
                        text_plain,
                        {
                            "rain_deficit": "rainfall_anomaly",
                            "heat": "heat",
                            "ndvi_dip": "ndvi",
                            "cloud_gap": "ndvi",
                            "bare_field": "ndvi",
                        }.get(finding["kind"], "data_gap"),
                    ),
                )
            if causes_info["suspected"]:
                conn.execute(
                    "UPDATE seasons SET suspected_cause = ? WHERE id = ?",
                    (causes_info["suspected"][0]["cause"], season_id),
                )

        complete_job(
            job_id,
            "done_with_gaps" if gaps else "done",
            {
                "season_id": season_id,
                "findings_count": len(findings),
                "gaps": gaps,
                "climate_cell_id": cell_id,
                "climate_years": [
                    int(history_weekly.index.get_level_values("year").min()),
                    int(history_weekly.index.get_level_values("year").max()),
                ],
            },
        )
    except Exception as exc:
        logger.exception("Season analysis failed for season %s", season_id)
        fail_job(job_id, str(exc))
