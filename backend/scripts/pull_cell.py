"""Pre-fetch and cache daily, weekly, and climatological NASA POWER data."""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.climate_service import (
    grid_cell_id,
    load_cell_normals,
    load_cell_weekly,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pull and cache climatological cell normals")
    parser.add_argument("--lat", type=float, default=9.50, help="Latitude")
    parser.add_argument("--lon", type=float, default=76.40, help="Longitude")
    parser.add_argument("--years", type=int, default=20, help="Years of daily history to pull")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Fetch fresh daily data instead of using the cell cache",
    )
    args = parser.parse_args()

    cell_id = grid_cell_id(args.lat, args.lon)
    print(f"Pulling NASA POWER history for {cell_id}...")
    normals = load_cell_normals(cell_id, refresh=args.refresh, years=args.years)
    weekly = load_cell_weekly(cell_id, years=args.years)
    years = weekly.index.get_level_values("year")
    print(
        f"Cached {len(weekly)} ISO weeks covering {years.min()}-{years.max()}; "
        f"52-week normals available for {', '.join(sorted(normals))}."
    )

if __name__ == "__main__":
    main()
