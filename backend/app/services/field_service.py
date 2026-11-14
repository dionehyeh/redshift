import json
import logging
from typing import Any
from uuid import uuid4

from app.db import get_db
from app.errors import AppError
from app.jobs import update_job_step, complete_job, fail_job
from app.engine.scoring import load_crops, hard_filter
from app.services.climate_service import load_cell_normals

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
        cell_lat = round(lat * 2) / 2   # snap to 0.5° grid
        cell_lon = round(lon * 2) / 2
        # Format: "09.5N_076.5E"
        lat_hem = "N" if cell_lat >= 0 else "S"
        lon_hem = "E" if cell_lon >= 0 else "W"
        cell_id = f"{abs(cell_lat):04.1f}{lat_hem}_{abs(cell_lon):05.1f}{lon_hem}"

        # Kerala lowland terrain defaults (demo — SRTM not called)
        elevation_m = 4.0
        slope = "low"
        is_flood_prone = True  # lowland Kerala default
        drainage = "poor"

        # Step 2: soil (40%) — SoilGrids demo defaults
        update_job_step(job_id, "soil", 40)
        soil_ph = 5.4
        soil_oc = 1.2
        soil_texture = "clay_loam"
        soil_source = "SoilGrids (demo default)"
        soil_confidence = "low"

        # Build profile_meta JSON for per-metric source/confidence tracking
        profile_meta = {
            "elevation_m": {"value": elevation_m, "source": "SRTM GL1 (demo default)", "resolution": "30 m", "confidence": "low"},
            "slope": {"value": slope, "source": "SRTM terrain model (demo)", "resolution": "30 m", "confidence": "low"},
            "flood_prone": {"value": is_flood_prone, "source": "SRTM + Historical Rain pattern (Kerala lowland)", "resolution": "regional", "confidence": "medium"},
            "drainage": {"value": drainage, "source": "KAU soil classification (Kerala lowland default)", "resolution": "regional", "confidence": "medium"},
            "soil_ph": {"value": soil_ph, "source": soil_source, "resolution": "250 m", "confidence": soil_confidence},
            "soil_oc": {"value": soil_oc, "source": soil_source, "resolution": "250 m", "confidence": soil_confidence},
            "soil_texture": {"value": soil_texture, "source": soil_source, "resolution": "250 m", "confidence": soil_confidence},
            "water_source": {"value": field.get("water_source", "unknown"), "source": "Farmer profile", "resolution": "field-level", "confidence": "high"},
            "water_quality": {"value": field.get("water_quality", "unknown"), "source": "Farmer profile", "resolution": "field-level", "confidence": "high"},
        }

        # Step 3: climate_normals (70%) — load or build demo normals
        update_job_step(job_id, "climate_normals", 70)
        normals = load_cell_normals(cell_id)
        tmean = normals.get("tmean", [27.5] * 52)

        # Step 4: feasibility scoring (90%)
        update_job_step(job_id, "feasibility", 90)
        crops = load_crops()

        # Build field dict for scoring engine (needs ph key too)
        field_eval = {
            "elevation_m": elevation_m,
            "flood_prone": is_flood_prone,
            "drainage": drainage,
            "soil_ph": soil_ph,
            "ph": soil_ph,  # scoring engine uses both keys
            "water_source": field.get("water_source", "rainfed"),
            "water_quality": field.get("water_quality", "unknown"),
            "slope": slope,
        }

        with get_db() as conn:
            # Update field with computed data
            conn.execute(
                """UPDATE fields SET
                   profile_status = 'ready',
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
                (cell_id, elevation_m, slope, int(is_flood_prone), drainage,
                 soil_ph, soil_oc, soil_texture, soil_source, soil_confidence,
                 json.dumps(profile_meta), field_id),
            )

            # Compute and store crop feasibility for all crops
            # Use week 2 as start, week 24 as next season (Kharif → Rabi example)
            start_week = 2
            next_week = 24
            tmean_window = tmean[:12]  # first 12 weeks for hard filter temperature check

            for crop in crops:
                cls, reasons = hard_filter(crop, field_eval, start_week, next_week, tmean_window)
                reason_str = "; ".join(reasons) if reasons else ("All conditions met" if cls == "suitable" else "Marginal conditions")
                windows_str = ";".join(f"{w[0]}-{w[1]}" for w in crop["start_windows"])

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

        complete_job(job_id, "done", {"field_id": field_id, "status": "ready", "cell_id": cell_id})

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
