import json
import logging
import math
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import requests

from app.db import get_db
from app.engine.scoring import hard_filter, load_crops
from app.errors import AppError
from app.jobs import complete_job, fail_job, update_job_step
from app.services.climate_service import grid_cell_id, load_cell_normals
from app.services.soil_service import (
    SoilDataUnavailable,
    estimate_drainage,
    fetch_soil_profile,
)
from app.services.terrain_service import TerrainDataUnavailable, fetch_terrain_profile

logger = logging.getLogger(__name__)

FIELD_COLUMNS = {
    "name",
    "lat",
    "lon",
    "water_source",
    "water_quality",
    "area_ha",
    "boundary_geojson",
}
SOIL_COLUMNS = {"soil_ph", "soil_oc", "soil_texture"}


def create_field_record(
    farmer_id: int,
    name: str,
    lat: float,
    lon: float,
    water_source: str,
    water_quality: str,
    area_ha: float | None,
    boundary_geojson: str | None,
) -> tuple[int, str]:
    with get_db() as conn:
        row = conn.execute(
            """INSERT INTO fields (
                   farmer_id, name, lat, lon, water_source, water_quality,
                   area_ha, boundary_geojson, profile_status
               )
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
               RETURNING id""",
            (
                farmer_id,
                name,
                lat,
                lon,
                water_source,
                water_quality,
                area_ha,
                boundary_geojson,
            ),
        ).fetchone()
        field_id = row["id"]
        job_id = f"job_field_{field_id}"
        conn.execute(
            """INSERT INTO jobs (id, kind, target_id, status, step, progress, steps_json)
               VALUES (?, 'field_onboarding', ?, 'queued', 'queued', 0, ?)""",
            (
                job_id,
                field_id,
                json.dumps(["terrain", "soil", "climate_normals", "feasibility"]),
            ),
        )
    return field_id, job_id


def list_field_records(farmer_id: int, status: str | None = None) -> list[dict[str, Any]]:
    query = """SELECT id, name, lat, lon, area_ha, profile_status, climate_cell_id,
                      water_source, created_at
               FROM fields
               WHERE farmer_id = ?"""
    params: tuple[Any, ...] = (farmer_id,)
    if status:
        query += " AND profile_status = ?"
        params += (status,)
    query += " ORDER BY created_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def update_field_record(
    field_id: int,
    farmer_id: int,
    field: dict[str, Any],
    updates: dict[str, Any],
    corrections: list[dict[str, Any]],
) -> str | None:
    if not set(updates).issubset(FIELD_COLUMNS):
        raise ValueError("Unsupported field update")
    if any(correction.get("key") not in SOIL_COLUMNS for correction in corrections):
        raise ValueError("Unsupported soil correction")

    metadata = field.get("profile_meta")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError as exc:
            logger.exception("Invalid profile metadata for field %s", field_id)
            raise AppError(
                "FIELD_PROFILE_INVALID",
                "Stored field profile metadata is invalid",
                status=500,
            ) from exc
    if metadata is None:
        metadata = {}
    elif not isinstance(metadata, dict):
        raise AppError(
            "FIELD_PROFILE_INVALID",
            "Stored field profile metadata is invalid",
            status=500,
        )

    coordinates_changed = any(
        key in updates and updates[key] != field.get(key)
        for key in ("lat", "lon")
    )
    if coordinates_changed and corrections:
        raise AppError(
            "VALIDATION",
            "Submit soil corrections after the updated coordinates finish processing",
            status=422,
        )
    field_updates = dict(updates)
    if updates.get("water_source") is not None:
        metadata["water_source"] = {
            "value": updates["water_source"],
            "source": "Farmer profile",
            "resolution": "field-level",
            "confidence": "high",
        }
    if updates.get("water_quality") is not None:
        metadata["water_quality"] = {
            "value": updates["water_quality"],
            "source": "Farmer profile",
            "resolution": "field-level",
            "confidence": "high",
        }

    with get_db() as conn:
        for correction in corrections:
            key = correction["key"]
            value = correction["value"]
            conn.execute(
                """INSERT INTO corrections (field_id, corrected_by, by_role, new_cause, note)
                   VALUES (?, ?, 'farmer', ?, ?)""",
                (
                    field_id,
                    farmer_id,
                    key,
                    correction.get("note") or f"Farmer correction: {value}",
                ),
            )
            field_updates[key] = value
            metadata[key] = {
                "value": value,
                "source": "Farmer correction",
                "resolution": "field-level",
                "confidence": "high",
            }

        if corrections:
            field_updates["soil_confidence"] = "high"
            field_updates["soil_source"] = "Farmer correction"

        job_id = None
        if coordinates_changed:
            metadata = {
                key: value
                for key, value in metadata.items()
                if key in {"water_source", "water_quality"}
            }
            field_updates.update(
                {
                    "profile_status": "pending",
                    "climate_cell_id": None,
                    "elevation_m": None,
                    "slope": None,
                    "flood_prone": 0,
                    "drainage": None,
                    "soil_ph": None,
                    "soil_oc": None,
                    "soil_texture": None,
                    "soil_source": None,
                    "soil_confidence": None,
                }
            )
            job_id = f"job_field_{field_id}_{uuid4().hex[:12]}"

        field_updates["profile_meta"] = json.dumps(metadata)
        set_clause = ", ".join(f"{column} = ?" for column in field_updates)
        conn.execute(
            f"UPDATE fields SET {set_clause} WHERE id = ?",
            (*field_updates.values(), field_id),
        )
        if job_id:
            conn.execute(
                """INSERT INTO jobs (id, kind, target_id, status, step, progress, steps_json)
                   VALUES (?, 'field_onboarding', ?, 'queued', 'queued', 0, ?)""",
                (
                    job_id,
                    field_id,
                    json.dumps(["terrain", "soil", "climate_normals", "feasibility"]),
                ),
            )
    return job_id


def list_feasible_crops(field_id: int) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT fc.crop_id, fc."class" AS crop_class, fc.reason, fc.start_windows,
                      fc.computed_at, c.name, c.name_ml, c.duration_days, c.water_need, c.family
               FROM field_crops fc
               JOIN crops c ON fc.crop_id = c.id
               WHERE fc.field_id = ?
               ORDER BY CASE fc."class"
                   WHEN 'suitable' THEN 1
                   WHEN 'marginal' THEN 2
                   ELSE 3
               END, c.name""",
            (field_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def list_field_history(field_id: int) -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT s.id, s.crop_id, s.field_id, s.status,
                      s.start_date::text, s.end_date::text, s.outcome,
                      s.loss_percent, s.suspected_cause, s.approval_status,
                      s.approved_cause, s.approver_role, s.investment, s.revenue,
                      s.created_at::text, c.name AS crop_name, c.name_ml, c.family,
                      u.name AS approved_by_name
               FROM seasons s
               LEFT JOIN crops c ON s.crop_id = c.id
               LEFT JOIN users u ON s.approved_by = u.id
               WHERE s.field_id = ?
               ORDER BY s.start_date DESC NULLS LAST, s.id DESC""",
            (field_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def onboard_field_task(job_id: str, field_id: int) -> None:
    try:
        with get_db() as conn:
            conn.execute(
                "UPDATE fields SET profile_status = 'building' WHERE id = ?",
                (field_id,),
            )

        # Step 1: terrain (15%) — snap lat/lon to 0.5° grid for climate cell
        update_job_step(job_id, "terrain", 15)
        with get_db() as conn:
            field = dict(conn.execute("SELECT * FROM fields WHERE id = ?", (field_id,)).fetchone())

        lat, lon = field["lat"], field["lon"]
        cell_id = grid_cell_id(lat, lon)
        gaps = []

        terrain = None
        update_job_step(job_id, "terrain", 15)
        try:
            terrain = fetch_terrain_profile(lat, lon)
        except TerrainDataUnavailable as exc:
            logger.warning("SRTM profile unavailable for field %s", field_id, exc_info=exc)
            gaps.append("SRTM terrain profile is unavailable")

        update_job_step(job_id, "soil", 40)
        soil = None
        try:
            soil = fetch_soil_profile(lat, lon)
        except SoilDataUnavailable as exc:
            logger.warning("SoilGrids profile unavailable for field %s", field_id, exc_info=exc)
            gaps.append("SoilGrids soil profile is unavailable")
        else:
            if any(
                soil.get(key) is None
                for key in ("soil_ph", "soil_oc", "soil_texture")
            ):
                gaps.append("SoilGrids soil properties are incomplete")

        elevation_m = terrain["elevation_m"] if terrain else None
        slope = terrain["slope"] if terrain else None
        slope_pct = terrain["slope_pct"] if terrain else None
        is_flood_prone = terrain["flood_prone"] if terrain else None
        relative_elevation = terrain["relative_elevation_m"] if terrain else None
        soil_ph = soil["soil_ph"] if soil else None
        soil_oc = soil["soil_oc"] if soil else None
        soil_texture = soil["soil_texture"] if soil else None
        soil_source = soil["source"] if soil else None
        soil_confidence = soil["confidence"] if soil else None
        clay_pct = soil["clay_pct"] if soil else None
        sand_pct = soil["sand_pct"] if soil else None
        drainage = estimate_drainage(clay_pct, sand_pct, slope_pct)
        if drainage is None:
            gaps.append("Soil texture and terrain do not support a drainage estimate")

        update_job_step(job_id, "climate_normals", 70)
        normals = {}
        try:
            normals = load_cell_normals(cell_id)
        except (RuntimeError, requests.RequestException) as exc:
            logger.warning("NASA POWER normals unavailable for field %s", field_id, exc_info=exc)
            gaps.append("NASA POWER climatology is unavailable")

        required_normals = ("rain_mm", "tmean", "tmax")
        climate_ready = all(
            key in normals
            and len(normals[key]) == 52
            and all(
                value is not None and math.isfinite(float(value))
                for value in normals[key]
            )
            for key in required_normals
        )
        if not climate_ready and "NASA POWER climatology is unavailable" not in gaps:
            gaps.append("NASA POWER climatology is incomplete")

        profile_meta = {
            "elevation_m": {
                "value": elevation_m,
                "source": terrain["source"] if terrain else "SRTM GL1",
                "resolution": "30 m",
                "confidence": terrain["confidence"] if terrain else "low",
            },
            "slope": {
                "value": slope,
                "source": "SRTM GL1 terrain model",
                "resolution": "30 m",
                "confidence": terrain["confidence"] if terrain else "low",
                "estimate": {"slope_pct": slope_pct},
            },
            "flood_prone": {
                "value": is_flood_prone,
                "source": "SRTM GL1 local-relief indicator",
                "resolution": "30 m",
                "confidence": "low",
                "estimate": {"relative_elevation_m": relative_elevation},
            },
            "drainage": {
                "value": drainage,
                "source": "SoilGrids texture + SRTM slope estimate",
                "resolution": "250 m + 30 m",
                "confidence": "low",
                "estimate": {"clay_pct": clay_pct, "slope_pct": slope_pct},
            },
            "soil_ph": {
                "value": soil_ph,
                "source": soil_source or "ISRIC SoilGrids v2.0",
                "resolution": "250 m",
                "confidence": soil_confidence or "low",
            },
            "soil_oc": {
                "value": soil_oc,
                "source": soil_source or "ISRIC SoilGrids v2.0",
                "resolution": "250 m",
                "confidence": soil_confidence or "low",
            },
            "soil_texture": {
                "value": soil_texture,
                "source": soil_source or "ISRIC SoilGrids v2.0",
                "resolution": "250 m",
                "confidence": soil_confidence or "low",
                "estimate": {
                    "clay_pct": clay_pct,
                    "sand_pct": sand_pct,
                    "silt_pct": soil["silt_pct"] if soil else None,
                },
            },
            "water_source": {"value": field.get("water_source", "unknown"), "source": "Farmer profile", "resolution": "field-level", "confidence": "high"},
            "water_quality": {"value": field.get("water_quality", "unknown"), "source": "Farmer profile", "resolution": "field-level", "confidence": "high"},
            "climate": {
                "source": "NASA POWER",
                "resolution": "~50 km",
                "normal_years": 20,
            },
            "gaps": gaps,
            "generated_at": datetime.now(UTC).isoformat(),
        }

        # A missing elevation or climatology is not replaced with a regional constant.
        profile_ready = elevation_m is not None and climate_ready
        update_job_step(job_id, "feasibility", 90)
        if profile_ready:
            crops = load_crops()
            field_eval = {
                "elevation_m": elevation_m,
                "flood_prone": is_flood_prone,
                "drainage": drainage,
                "soil_ph": soil_ph,
                "ph": soil_ph,
                "water_source": field.get("water_source", "unknown"),
                "water_quality": field.get("water_quality", "unknown"),
                "slope": slope,
            }
            tmean_window = normals["tmean"][:12]

        with get_db() as conn:
            conn.execute(
                """UPDATE fields SET
                   profile_status = ?,
                   climate_cell_id = ?,
                   elevation_m = ?,
                   slope = ?,
                   flood_prone = ?,
                   drainage = ?,
                   soil_ph = ?,
                   soil_oc = ?,
                   soil_texture = ?,
                   soil_source = ?,
                   soil_confidence = ?,
                   profile_meta = ?
                   WHERE id = ?""",
                (
                    "ready" if profile_ready else "failed",
                    cell_id,
                    elevation_m,
                    slope,
                    int(is_flood_prone) if is_flood_prone is not None else None,
                    drainage,
                    soil_ph,
                    soil_oc,
                    soil_texture,
                    soil_source,
                    soil_confidence,
                    json.dumps(profile_meta),
                    field_id,
                ),
            )

            if profile_ready:
                for crop in crops:
                    cls, reasons = hard_filter(
                        crop,
                        field_eval,
                        2,
                        24,
                        tmean_window,
                    )
                    reason_str = "; ".join(reasons) if reasons else (
                        "All conditions met" if cls == "suitable" else "Marginal conditions"
                    )
                    windows_str = ";".join(
                        f"{window[0]}-{window[1]}" for window in crop["start_windows"]
                    )
                    conn.execute(
                        """INSERT INTO field_crops (field_id, crop_id, "class", reason, start_windows, computed_at)
                           VALUES (?, (SELECT id FROM crops WHERE name = ?), ?, ?, ?, CURRENT_TIMESTAMP)
                           ON CONFLICT (field_id, crop_id) DO UPDATE SET
                               "class" = EXCLUDED."class",
                               reason = EXCLUDED.reason,
                               start_windows = EXCLUDED.start_windows,
                               computed_at = CURRENT_TIMESTAMP""",
                        (field_id, crop["name"], cls, reason_str, windows_str),
                    )

        status = "ready" if profile_ready else "failed"
        job_status = "done_with_gaps" if gaps else "done"
        complete_job(
            job_id,
            job_status,
            {"field_id": field_id, "status": status, "cell_id": cell_id, "gaps": gaps},
        )

    except Exception as exc:
        logger.exception("Field onboarding failed for field %s", field_id)
        try:
            with get_db() as conn:
                conn.execute(
                    "UPDATE fields SET profile_status = 'failed' WHERE id = ?",
                    (field_id,),
                )
        except Exception:
            logger.exception(
                "Could not mark field %s as failed after onboarding error",
                field_id,
            )
        fail_job(job_id, str(exc))
