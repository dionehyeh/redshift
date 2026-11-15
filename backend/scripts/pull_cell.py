"""Fetch NASA POWER daily data and build a cell's weekly climatology cache."""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import requests

from app.config import settings
from app.services.climate_service import (
    grid_cell_id,
    load_cell_daily,
    load_cell_normals,
    load_cell_weekly,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch NASA POWER observations and cache weekly climatology"
    )
    parser.add_argument("--lat", type=float, required=True, help="Field latitude")
    parser.add_argument("--lon", type=float, required=True, help="Field longitude")
    parser.add_argument(
        "--years",
        type=int,
        default=20,
        help="Number of years to fetch (default: 20)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh cached daily and weekly data",
    )
    args = parser.parse_args()
    if args.years < 1:
        parser.error("--years must be a positive integer")

    try:
        cell_id = grid_cell_id(args.lat, args.lon)
        daily = load_cell_daily(cell_id, refresh=args.refresh, years=args.years)
        weekly = load_cell_weekly(cell_id, refresh=args.refresh, years=args.years)
        normals = load_cell_normals(cell_id, refresh=args.refresh, years=args.years)
    except (OSError, requests.RequestException, RuntimeError, ValueError) as exc:
        parser.error(f"Could not prefetch NASA POWER data: {exc}")

    start = pd.Timestamp(daily.index.min()).date()
    end = pd.Timestamp(daily.index.max()).date()
    variables = ", ".join(sorted(normals))
    print(f"Cached NASA POWER cell {cell_id}")
    print(f"Observed range: {start} through {end} ({len(daily)} daily records)")
    print(f"Weekly records: {len(weekly)}")
    print(f"52-week climatology variables: {variables}")
    print(f"Cache directory: {Path(settings.cache_dir).resolve()}")


if __name__ == "__main__":
    main()
