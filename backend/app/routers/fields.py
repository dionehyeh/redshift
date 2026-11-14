import json
from fastapi import APIRouter, Depends, BackgroundTasks
from app.schemas.fields import (
    FieldCreateRequest,
    FieldPatchRequest,
    FieldProfileResponse,
    FeasibleCropsResponse,
)
from app.deps import current_user, require_role, own_field
from app.db import get_db
from app.jobs import create_job
from app.services.field_service import onboard_field_task

router = APIRouter(prefix="/fields", tags=["Fields"])

@router.post("", status_code=202)
def create_field(body: FieldCreateRequest, tasks: BackgroundTasks, user: dict = Depends(require_role("farmer"))):
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO fields (farmer_id, name, lat, lon, water_source, water_quality, area_ha, boundary_geojson)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            (user["id"], body.name, body.lat, body.lon, body.water_source, body.water_quality, body.area_ha, body.boundary_geojson),
        )
        field_id = cursor.fetchone()["id"]

    job_id = f"job_field_{field_id}"
    create_job(job_id, "field_onboarding", target_id=field_id, steps=["terrain", "soil", "climate_normals", "feasibility"])
    tasks.add_task(onboard_field_task, job_id, field_id)

    return {"field_id": field_id, "job_id": job_id, "status": "queued"}

@router.get("")
def list_fields(user: dict = Depends(require_role("farmer"))):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM fields WHERE farmer_id = ? ORDER BY created_at DESC", (user["id"],)).fetchall()
        return {"items": [dict(r) for r in rows], "next_cursor": None}

@router.get("/{id}")
def get_field_profile(id: int, field: dict = Depends(own_field)):
    profile = {
        "elevation_m": {"value": field.get("elevation_m") or 4.0, "source": "SRTM GL1", "resolution": "30 m", "confidence": "high"},
        "flood_prone": {"value": bool(field.get("flood_prone")), "source": "SRTM + Historical Rain", "confidence": "medium"},
        "soil_ph": {"value": field.get("soil_ph") or 5.4, "source": field.get("soil_source") or "SoilGrids estimate", "confidence": field.get("soil_confidence") or "low"},
        "drainage": {"value": field.get("drainage") or "poor", "source": "KAU / Terrain model", "confidence": "medium"},
        "water_source": {"value": field.get("water_source") or "rainfed", "source": "Farmer profile", "confidence": "high"},
        "water_quality": {"value": field.get("water_quality") or "unknown", "source": "Farmer profile", "confidence": "high"},
    }
    return {
        "id": field["id"],
        "farmer_id": field["farmer_id"],
        "name": field["name"],
        "lat": field["lat"],
        "lon": field["lon"],
        "area_ha": field.get("area_ha"),
        "water_source": field["water_source"],
        "water_quality": field["water_quality"],
        "profile_status": field["profile_status"],
        "profile": profile,
        "climate_cell_id": field.get("climate_cell_id"),
        "created_at": field["created_at"],
    }

@router.patch("/{id}")
def patch_field(id: int, body: FieldPatchRequest, user: dict = Depends(require_role("farmer")), field: dict = Depends(own_field)):
    with get_db() as conn:
        if body.name or body.water_source or body.water_quality:
            conn.execute(
                """UPDATE fields 
                   SET name = COALESCE(?, name),
                       water_source = COALESCE(?, water_source),
                       water_quality = COALESCE(?, water_quality)
                   WHERE id = ?""",
                (body.name, body.water_source, body.water_quality, id),
            )
        if body.corrections:
            for corr in body.corrections:
                conn.execute(
                    """INSERT INTO corrections (field_id, corrected_by, by_role, new_cause, note)
                       VALUES (?, ?, 'farmer', ?, ?)""",
                    (id, user["id"], corr.key, f"Manual correction: {corr.value} ({corr.note or ''})"),
                )
    return {"status": "updated"}

@router.get("/{id}/feasible-crops")
def get_feasible_crops(id: int, field: dict = Depends(own_field)):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT fc.*, c.name, c.name_ml, c.duration_days 
               FROM field_crops fc 
               JOIN crops c ON fc.crop_id = c.id 
               WHERE fc.field_id = ?""",
            (id,),
        ).fetchall()
        
        crops_list = []
        for r in rows:
            crops_list.append({
                "crop": r["name"],
                "name_ml": r["name_ml"],
                "class": r["class"],
                "reason": r["reason"],
                "start_windows": r["start_windows"].split(";") if r["start_windows"] else [],
                "duration_days": [r["duration_days"]],
            })
            
        return {"field_id": id, "computed_at": "2026-11-14", "crops": crops_list}

@router.get("/{id}/timeline")
def get_field_timeline(id: int, season_id: int | None = None, field: dict = Depends(own_field)):
    # 52-week normalized timeline series
    rain_vals = [20, 15, 12, 10, 8, 14, 22, 35, 60, 95, 140, 200, 280, 310, 290, 260] + [40] * 36
    return {
        "weeks": list(range(1, 53)),
        "series": {
            "rain_mm": {"values": rain_vals, "source": "GPM IMERG", "resolution": "~10 km"},
            "t2m": {"values": [27.5] * 52, "source": "NASA POWER", "resolution": "~50 km"},
            "ndvi": {"values": [0.45] * 52, "source": "MODIS", "resolution": "250 m"},
        },
        "bands": [
            {"kind": "stress", "from": 6, "to": 8, "label": "Rain deficit (40% below normal)"},
            {"kind": "cloud_gap", "from": 9, "to": 10, "label": "Cloud cover (no satellite image)"},
        ],
    }

@router.get("/{id}/map")
def get_field_map(id: int, field: dict = Depends(own_field)):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [field["lon"], field["lat"]],
                },
                "properties": {
                    "name": field["name"],
                    "elevation_m": field.get("elevation_m", 4.0),
                    "flood_prone": bool(field.get("flood_prone")),
                },
            }
        ],
    }

@router.get("/{id}/history")
def get_field_history(id: int, field: dict = Depends(own_field)):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT s.*, c.name as crop_name 
               FROM seasons s 
               LEFT JOIN crops c ON s.crop_id = c.id 
               WHERE s.field_id = ? 
               ORDER BY s.start_date DESC""",
            (id,),
        ).fetchall()
        return {"seasons": [dict(r) for r in rows]}
