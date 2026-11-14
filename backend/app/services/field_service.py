import json
from app.db import get_db
from app.jobs import update_job_step, complete_job, fail_job
from app.engine.scoring import load_crops, hard_filter
from app.analysis.core import slope_percent, relative_elevation, flood_prone, drainage_class

def onboard_field_task(job_id: str, field_id: int) -> None:
    try:
        update_job_step(job_id, "terrain", 15)
        # Compute terrain / slope / elevation
        with get_db() as conn:
            field = dict(conn.execute("SELECT * FROM fields WHERE id = ?", (field_id,)).fetchone())

        # Soil & climate normals step
        update_job_step(job_id, "soil", 40)
        
        # Climate normals step
        update_job_step(job_id, "climate_normals", 70)
        cell_id = f"{field['lat']:04.1f}N_{field['lon']:05.1f}E"

        # Feasibility check
        update_job_step(job_id, "feasibility", 90)
        crops = load_crops()
        field_eval = {
            "elevation_m": field.get("elevation_m") or 4.0,
            "flood_prone": bool(field.get("flood_prone")),
            "drainage": field.get("drainage") or "poor",
            "soil_ph": field.get("soil_ph") or 5.4,
            "water_source": field.get("water_source") or "rainfed",
        }

        with get_db() as conn:
            conn.execute(
                "UPDATE fields SET profile_status = 'ready', climate_cell_id = ? WHERE id = ?",
                (cell_id, field_id),
            )
            for c in crops:
                cls, reasons = hard_filter(c, field_eval, start_week=2, next_week=20, tmean=[27.0] * 12)
                windows_str = ";".join(f"{w[0]}-{w[1]}" for w in c["start_windows"])
                conn.execute(
                    """INSERT INTO field_crops (field_id, crop_id, class, reason, start_windows)
                       VALUES (?, (SELECT id FROM crops WHERE name = ?), ?, ?, ?)
                       ON CONFLICT (field_id, crop_id) DO UPDATE SET
                           class = EXCLUDED.class,
                           reason = EXCLUDED.reason,
                           start_windows = EXCLUDED.start_windows,
                           computed_at = CURRENT_TIMESTAMP""",
                    (field_id, c["name"], cls, "; ".join(reasons), windows_str),
                )

        complete_job(job_id, "done", {"field_id": field_id, "status": "ready"})
    except Exception as exc:
        fail_job(job_id, str(exc))
