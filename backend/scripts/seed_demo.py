import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db import get_db, init_db
from app.engine.scoring import load_crops


def seed() -> None:
    print("Initializing Neon PostgreSQL schema...")
    init_db()

    with get_db() as conn:
        print("Seeding crop catalog...")
        for crop in load_crops("data/crops.csv"):
            conn.execute(
                """INSERT INTO crops (
                    name, family, duration_days, need_mm, water_need, drought_tol, waterlog_tol,
                    n_effect, ph_min, ph_max, t_min, t_max, t_flower_max, flower_frac_start, flower_frac_end,
                    start_windows, long_duration, watch_for, elev_min, elev_max, repeat_penalty,
                    om_bonus, erosion_cover, market, salinity_tol, good_next, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (name) DO UPDATE SET
                    family = EXCLUDED.family,
                    duration_days = EXCLUDED.duration_days,
                    need_mm = EXCLUDED.need_mm,
                    water_need = EXCLUDED.water_need,
                    drought_tol = EXCLUDED.drought_tol,
                    waterlog_tol = EXCLUDED.waterlog_tol,
                    n_effect = EXCLUDED.n_effect,
                    ph_min = EXCLUDED.ph_min,
                    ph_max = EXCLUDED.ph_max,
                    t_min = EXCLUDED.t_min,
                    t_max = EXCLUDED.t_max,
                    t_flower_max = EXCLUDED.t_flower_max,
                    flower_frac_start = EXCLUDED.flower_frac_start,
                    flower_frac_end = EXCLUDED.flower_frac_end,
                    start_windows = EXCLUDED.start_windows,
                    long_duration = EXCLUDED.long_duration,
                    watch_for = EXCLUDED.watch_for,
                    elev_min = EXCLUDED.elev_min,
                    elev_max = EXCLUDED.elev_max,
                    repeat_penalty = EXCLUDED.repeat_penalty,
                    om_bonus = EXCLUDED.om_bonus,
                    erosion_cover = EXCLUDED.erosion_cover,
                    market = EXCLUDED.market,
                    salinity_tol = EXCLUDED.salinity_tol,
                    good_next = EXCLUDED.good_next,
                    source = EXCLUDED.source""",
                (
                    crop["name"],
                    crop["family"],
                    crop["duration_days"],
                    crop["need_mm"],
                    crop["water_need"],
                    crop["drought_tol"],
                    crop["waterlog_tol"],
                    crop["n_effect"],
                    crop["ph_min"],
                    crop["ph_max"],
                    crop["t_min"],
                    crop["t_max"],
                    crop["t_flower_max"],
                    crop["flower_frac"][0],
                    crop["flower_frac"][1],
                    ";".join(f"{window[0]}-{window[1]}" for window in crop["start_windows"]),
                    int(crop["long_duration"]),
                    ";".join(crop["watch_for"]),
                    crop["elev_min"],
                    crop["elev_max"],
                    crop["repeat_penalty"],
                    int(crop["om_bonus"]),
                    int(crop["erosion_cover"]),
                    crop["market"],
                    crop["salinity_tol"],
                    ";".join(crop["good_next"]),
                    "KAU Package of Practices 2026",
                ),
            )

    print("Crop catalog seeded. Create users through Clerk; demo passwords are disabled.")


if __name__ == "__main__":
    seed()
