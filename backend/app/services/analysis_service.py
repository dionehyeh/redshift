"""Season diagnosis using observed weekly climate and historical normals."""

import logging
import re
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from app.analysis.core import (
    anomalies,
    build_findings,
    clean_daily,
    likely_causes,
    water_confidence,
    weekly_normals,
)
from app.db import get_db
from app.engine.scoring import load_crops
from app.jobs import complete_job, fail_job, update_job_step
from app.services.climate_service import load_cell_weekly, load_point_imerg_weekly
from app.services.earth_engine_service import EarthObservationDataUnavailable

logger = logging.getLogger(__name__)
WEATHER_COLUMNS = ("rain_mm", "tmean", "tmax")


def _as_date(value: Any, label: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Season {label} must be a valid ISO date") from exc


def _week_keys(start: date, end: date) -> list[tuple[int, int]]:
    dates = pd.date_range(start, end, freq="D")
    iso = dates.isocalendar()
    keys = []
    for year, week in zip(iso["year"], iso["week"]):
        key = (int(year), min(int(week), 52))
        if not keys or keys[-1] != key:
            keys.append(key)
    return keys


def _finite_values(values: pd.Series) -> list[float]:
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    return [float(value) if np.isfinite(value) else float("nan") for value in numeric]


def _minimum_normal_years(normals: pd.DataFrame, column: str, weeks: list[int]) -> int:
    counts = normals[(column, "count")].reindex(weeks)
    valid = counts[np.isfinite(counts.to_numpy(dtype=float))]
    return int(valid.min()) if not valid.empty else 0


def analyze_weekly_data(
    weekly: pd.DataFrame,
    start_date: date,
    end_date: date,
    crop: dict,
    rainfall_observations: dict[tuple[int, int], float | None] | None = None,
    rain_source: str = "NASA POWER",
    rain_resolution: str = "~50 km",
) -> tuple[list[dict], list[str], str]:
    """Build findings from a season window and its available historical weekly series."""
    if start_date > end_date:
        raise ValueError("Season start_date must not be after end_date")
    if not isinstance(weekly.index, pd.MultiIndex) or not {"year", "week"}.issubset(
        weekly.index.names
    ):
        raise ValueError("Weekly climate data must use a year/week MultiIndex")
    if weekly.empty:
        raise ValueError("Weekly climate data cannot be empty")

    supported = [column for column in (*WEATHER_COLUMNS, "ndvi") if column in weekly]
    if not any(column in supported for column in ("rain_mm", "tmax")):
        raise ValueError("Weekly climate data has no rainfall or maximum temperature")

    analysis_weekly = clean_daily(weekly.copy())
    normal_frame = weekly_normals(analysis_weekly, supported)
    keys = _week_keys(start_date, end_date)
    week_index = pd.MultiIndex.from_tuples(keys, names=["year", "week"])
    observed = analysis_weekly.reindex(week_index)
    if "rain_mm" in observed and rainfall_observations:
        for key, value in rainfall_observations.items():
            if key in observed.index and value is not None:
                observed.loc[key, "rain_mm"] = value
    weeks = [week for _, week in keys]
    gaps: list[str] = []
    source_meta = {}

    def metric(column: str, finding: str, source: str, resolution: str) -> list[float]:
        if column not in observed:
            gaps.append(f"{column} observations are unavailable")
            return [float("nan")] * len(keys)
        anomaly = anomalies(observed[[column]], normal_frame, column)
        years = _minimum_normal_years(normal_frame, column, weeks)
        source_meta[finding] = {
            "source": source,
            "resolution": resolution,
            "confidence": water_confidence(years),
        }
        missing = ~np.isfinite(pd.to_numeric(observed[column], errors="coerce").to_numpy(dtype=float))
        missing_runs = []
        run_start = None
        for index, is_missing in enumerate(list(missing) + [False]):
            if is_missing and run_start is None:
                run_start = index
            elif not is_missing and run_start is not None:
                missing_runs.append((run_start, index - 1))
                run_start = None
        gaps.extend(
            f"{column} observations are missing in weeks {weeks[first]} to {weeks[last]}"
            for first, last in missing_runs
        )
        if years < 10:
            gaps.append(f"Historical {column} normals cover fewer than 10 years")
        return _finite_values(anomaly["z"])

    rain_z = metric(
        "rain_mm",
        "rain_deficit",
        rain_source,
        rain_resolution,
    )
    rain_frame = (
        anomalies(observed[["rain_mm"]], normal_frame, "rain_mm")
        if "rain_mm" in observed
        else None
    )
    rain_pct = (
        _finite_values(rain_frame["pct"])
        if rain_frame is not None
        else [float("nan")] * len(keys)
    )
    tmax = (
        _finite_values(observed["tmax"])
        if "tmax" in observed
        else [float("nan")] * len(keys)
    )
    if "tmax" in observed:
        metric("tmax", "heat", "NASA POWER", "~50 km")
    else:
        gaps.append("Maximum temperature observations are unavailable")

    ndvi_values: list[float] | None = None
    ndvi_z: list[float] | None = None
    if "ndvi" in observed:
        values = pd.to_numeric(observed["ndvi"], errors="coerce")
        observed_ndvi = observed.assign(ndvi=values)
        ndvi_anomaly = anomalies(observed_ndvi[["ndvi"]], normal_frame, "ndvi")
        ndvi_values = _finite_values(values)
        ndvi_z = _finite_values(ndvi_anomaly["z"])
        years = _minimum_normal_years(normal_frame, "ndvi", weeks)
        source_meta.update(
            {
                kind: {
                    "source": "MODIS (MOD13Q1)",
                    "resolution": "250 m",
                    "confidence": water_confidence(years),
                }
                for kind in ("ndvi_dip", "cloud_gap", "bare_field")
            }
        )
        if years < 10:
            gaps.append("Historical NDVI normals cover fewer than 10 years")

    findings, finding_gaps = build_findings(
        weeks,
        rain_z,
        rain_pct,
        tmax,
        ndvi_values,
        ndvi_z,
        crop,
        source_meta,
    )
    gaps.extend(finding_gaps)
    years = sorted(int(year) for year in weekly.index.get_level_values("year").unique())
    comparison = f"{years[0]}-{years[-1]} ({len(years)}-year climatology)"
    return findings, list(dict.fromkeys(gaps)), comparison


def _deviation_value(finding: dict) -> float | None:
    match = re.match(r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))", str(finding.get("deviation", "")))
    return float(match.group(1)) if match else None


def _finding_text(finding: dict) -> tuple[str | None, str | None]:
    kind = finding["kind"]
    deviation = finding.get("deviation")
    weeks = f"weeks {finding['weeks'][0]} to {finding['weeks'][1]}"
    if kind == "rain_deficit":
        return f"Rainfall was {deviation} below normal in {weeks}.", "rainfall_anomaly"
    if kind == "heat":
        return f"Maximum temperature exceeded the flowering heat limit in {weeks} ({deviation}).", "normals"
    if kind == "ndvi_dip":
        return f"Satellite greenness was below normal in {weeks}.", "ndvi"
    if kind == "cloud_gap":
        return f"No clear satellite image was available in {weeks}.", "cloud_gaps"
    if kind == "bare_field":
        return f"Satellite images showed low vegetation cover in {weeks}.", "ndvi"
    return None, None


def analyze_season_task(job_id: str, season_id: int) -> None:
    try:
        update_job_step(job_id, "loading_season", 20)
        with get_db() as conn:
            row = conn.execute(
                """SELECT s.*, c.name AS crop_name, f.climate_cell_id, f.lat, f.lon
                   FROM seasons s
                   JOIN fields f ON f.id = s.field_id
                   LEFT JOIN crops c ON c.id = s.crop_id
                   WHERE s.id = ?""",
                (season_id,),
            ).fetchone()
        if not row:
            raise ValueError(f"Season {season_id} does not exist")
        season = dict(row)
        if not season.get("crop_name"):
            raise ValueError("Season crop is missing from the crop catalog")
        if not season.get("climate_cell_id"):
            raise ValueError("Field climate profile is not ready")
        start = _as_date(season.get("start_date"), "start_date")
        end = _as_date(season.get("end_date"), "end_date")
        crops = {crop["name"]: crop for crop in load_crops()}
        crop = crops.get(season["crop_name"])
        if crop is None:
            raise ValueError(f"Crop {season['crop_name']} is missing from the analysis catalog")

        update_job_step(job_id, "calculating_anomalies", 50)
        point = (season["lat"], season["lon"])
        weekly = load_cell_weekly(season["climate_cell_id"], point=point)
        season_keys = set(_week_keys(start, end))
        rainfall_observations = {}
        rain_source = "NASA POWER"
        rain_resolution = "~50 km"
        for year in range(start.isocalendar().year, end.isocalendar().year + 1):
            try:
                imerg = load_point_imerg_weekly(point[0], point[1], year)
            except EarthObservationDataUnavailable as exc:
                logger.warning(
                    "GPM IMERG unavailable for field %s in %s; retaining NASA POWER observations",
                    season_id,
                    year,
                    exc_info=exc,
                )
                continue
            rainfall_observations.update(
                {
                    (year, week): value
                    for week, value in imerg.items()
                    if value is not None and (year, week) in season_keys
                }
            )
        if rainfall_observations:
            rain_source = (
                "NASA GPM IMERG observations (provisional status possible) "
                "with NASA POWER gap fallback"
            )
            rain_resolution = "~11 km IMERG; ~50 km POWER normals"
        findings, gaps, comparison_years = analyze_weekly_data(
            weekly,
            start,
            end,
            crop,
            rainfall_observations,
            rain_source,
            rain_resolution,
        )
        update_job_step(job_id, "synthesizing_stress_flags", 80)
        causes = likely_causes(findings, season.get("suspected_cause"))

        with get_db() as conn:
            existing_rows = conn.execute(
                """SELECT id, kind, week_from, week_to, review_status
                   FROM findings WHERE season_id = ?""",
                (season_id,),
            ).fetchall()
            existing = {
                (row["kind"], row["week_from"], row["week_to"]): dict(row)
                for row in existing_rows
            }
            finding_keys = set()
            for finding in findings:
                text, explainer_key = _finding_text(finding)
                unit = "%" if finding["kind"] == "rain_deficit" else "°C" if finding["kind"] == "heat" else None
                key = (finding["kind"], finding["weeks"][0], finding["weeks"][1])
                finding_keys.add(key)
                values = (
                    _deviation_value(finding),
                    unit,
                    finding["crop_stage"],
                    str(finding["severity"]),
                    finding["confidence"],
                    finding["source"],
                    finding["resolution"],
                    text,
                    explainer_key,
                )
                previous = existing.get(key)
                if previous:
                    conn.execute(
                        """UPDATE findings SET deviation = ?, unit = ?, crop_stage = ?,
                               severity = ?, confidence = ?, source = ?, resolution = ?,
                               text_plain = ?, explainer_key = ?
                           WHERE id = ?""",
                        (*values, previous["id"]),
                    )
                else:
                    conn.execute(
                        """INSERT INTO findings (
                               season_id, kind, week_from, week_to, deviation, unit,
                               crop_stage, severity, confidence, source, resolution,
                               text_plain, explainer_key
                           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            season_id,
                            *key,
                            *values,
                        ),
                    )
            for key, previous in existing.items():
                if key not in finding_keys and previous["review_status"] == "pending":
                    conn.execute("DELETE FROM findings WHERE id = ?", (previous["id"],))

        result = {
            "season_id": season_id,
            "findings_count": len(findings),
            "gaps": gaps,
            "comparison_years": comparison_years,
            "likely_causes": causes,
        }
        complete_job(job_id, "done_with_gaps" if gaps else "done", result)
    except Exception:
        logger.exception("Season analysis failed for season %s", season_id)
        fail_job(job_id, "Season analysis failed; check server logs for details")
