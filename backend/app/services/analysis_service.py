from app.db import get_db
from app.jobs import update_job_step, complete_job, fail_job
from app.analysis.core import build_findings, likely_causes
from app.engine.scoring import load_crops

def analyze_season_task(job_id: str, season_id: int) -> None:
    try:
        update_job_step(job_id, "loading_season", 20)
        with get_db() as conn:
            season = dict(conn.execute("SELECT * FROM seasons WHERE id = ?", (season_id,)).fetchone())
            crop_name = season["crop_id"]
            if isinstance(crop_name, int):
                row = conn.execute("SELECT name FROM crops WHERE id = ?", (crop_name,)).fetchone()
                crop_name = row["name"] if row else "paddy"
            else:
                crop_name = crop_name or "paddy"

        update_job_step(job_id, "calculating_anomalies", 50)
        crops = {c["name"]: c for c in load_crops()}
        target_crop = crops.get(crop_name, crops["paddy"])

        # Simulated or fixture season series for demo field
        season_weeks = list(range(1, 16))
        rain_z = [-0.2, -0.4, -0.1, -1.2, -1.5, -1.4, -0.8, -0.3, -0.1, 0.2, 0.1, -0.2, -0.3, -0.1, 0.0]
        rain_pct = [-10, -20, -5, -42, -55, -48, -25, -10, -5, 10, 5, -8, -12, -4, 0]
        tmax = [32.0, 32.5, 33.0, 33.5, 34.0, 34.5, 33.8, 33.0, 32.5, 32.0, 31.5, 31.0, 31.0, 31.5, 32.0]
        ndvi = [0.28, 0.35, 0.45, 0.52, 0.58, 0.62, 0.60, 0.55, None, None, 0.50, 0.48, 0.42, 0.35, 0.25]
        ndvi_z = [-0.1, 0.0, 0.1, 0.2, 0.1, -0.2, -0.8, -1.3, np_nan_placeholder := 0.0, 0.0, -0.9, -0.7, -0.5, -0.2, 0.0]

        source_meta = {
            "rain_deficit": {"source": "GPM IMERG", "resolution": "~10 km", "confidence": "medium"},
            "heat": {"source": "NASA POWER", "resolution": "~50 km", "confidence": "high"},
            "ndvi_dip": {"source": "MODIS (MOD13Q1)", "resolution": "250 m", "confidence": "medium"},
        }

        update_job_step(job_id, "synthesizing_stress_flags", 80)
        findings, gaps = build_findings(season_weeks, rain_z, rain_pct, tmax, ndvi, ndvi_z, target_crop, source_meta)
        causes_info = likely_causes(findings, season.get("suspected_cause"))

        with get_db() as conn:
            for f in findings:
                text_plain = f"Rainfall deficit of {f.get('deviation')} detected in weeks {f['weeks'][0]} to {f['weeks'][1]}."
                conn.execute(
                    """INSERT INTO findings (season_id, kind, week_from, week_to, deviation, unit, crop_stage, severity, confidence, source, resolution, text_plain, explainer_key)
                       VALUES (?, ?, ?, ?, ?, '%', ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        season_id,
                        f["kind"],
                        f["weeks"][0],
                        f["weeks"][1],
                        float(str(f.get("deviation", "0")).replace("%", "")),
                        f["crop_stage"],
                        str(f["severity"]),
                        f["confidence"],
                        f["source"],
                        f["resolution"],
                        text_plain,
                        "rainfall_anomaly" if f["kind"] == "rain_deficit" else "ndvi",
                    ),
                )
            if causes_info["suspected"]:
                top_cause = causes_info["suspected"][0]["cause"]
                conn.execute("UPDATE seasons SET suspected_cause = ? WHERE id = ?", (top_cause, season_id))

        complete_job(job_id, "done", {"season_id": season_id, "findings_count": len(findings)})
    except Exception as exc:
        fail_job(job_id, str(exc))
