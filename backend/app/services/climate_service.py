"""NASA POWER daily weather retrieval and cached weekly climatology."""

import logging
import math
import os
import re
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from app.analysis.core import clean_daily, normals_arrays, to_weekly, weekly_normals
from app.config import settings

POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
CELL_ID_PATTERN = re.compile(r"^(\d{2}\.\d)([NS])_(\d{3}\.\d)([EW])$")
POWER_PARAMETERS = {
    "PRECTOTCORR": "rain_mm",
    "T2M": "tmean",
    "T2M_MAX": "tmax",
}
logger = logging.getLogger(__name__)


class ClimateDataUnavailable(RuntimeError):
    """Raised when neither observed weather data nor its normals can be loaded."""


def grid_cell_id(lat: float, lon: float, resolution: float = 0.5) -> str:
    """Return a stable geographic cell ID for a point and grid resolution."""
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError("latitude or longitude is out of range")
    if not math.isfinite(resolution) or resolution <= 0:
        raise ValueError("resolution must be a positive finite number")
    if not math.isclose(resolution * 10, round(resolution * 10)):
        raise ValueError("resolution must be representable to one decimal place")

    cell_lat = _snap(lat, resolution)
    cell_lon = _snap(lon, resolution)
    lat_hem = "N" if cell_lat >= 0 else "S"
    lon_hem = "E" if cell_lon >= 0 else "W"
    return f"{abs(cell_lat):04.1f}{lat_hem}_{abs(cell_lon):05.1f}{lon_hem}"


def _snap(coordinate: float, resolution: float) -> float:
    cells = math.floor(abs(coordinate) / resolution + 0.5)
    return math.copysign(round(cells * resolution, 4), coordinate)


def cell_coordinates(cell_id: str) -> tuple[float, float]:
    match = CELL_ID_PATTERN.fullmatch(cell_id)
    if not match:
        raise ValueError("Invalid climate cell ID")
    lat, lat_hem, lon, lon_hem = match.groups()
    latitude = float(lat) * (1 if lat_hem == "N" else -1)
    longitude = float(lon) * (1 if lon_hem == "E" else -1)
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise ValueError("Climate cell coordinates are out of range")
    return latitude, longitude


def get_cell_path(cell_id: str, kind: str = "normals") -> str:
    cell_coordinates(cell_id)
    if not re.fullmatch(r"[a-z_]+", kind):
        raise ValueError("Invalid climate cache kind")
    os.makedirs(settings.cache_dir, exist_ok=True)
    return os.path.join(settings.cache_dir, f"{cell_id}_{kind}.parquet")


def _read_parquet(path: str) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    if not isinstance(frame.index, pd.DatetimeIndex):
        if "date" in frame.columns:
            frame = frame.set_index(pd.to_datetime(frame.pop("date")))
        else:
            frame.index = pd.to_datetime(frame.index)
    frame.index.name = "date"
    return frame.sort_index()


def _write_parquet_atomic(frame: pd.DataFrame, path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent, suffix=".parquet", delete=False
        ) as temporary:
            temporary_path = temporary.name
        frame.to_parquet(temporary_path)
        os.replace(temporary_path, target)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)


def fetch_power_daily(
    lat: float,
    lon: float,
    start_date: date,
    end_date: date,
    timeout: float = 30,
) -> pd.DataFrame:
    """Fetch and normalize daily NASA POWER rain and temperature observations."""
    if start_date > end_date:
        raise ValueError("start_date must not be after end_date")
    response = requests.get(
        POWER_DAILY_URL,
        params={
            "parameters": ",".join(POWER_PARAMETERS),
            "community": "AG",
            "longitude": lon,
            "latitude": lat,
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "format": "JSON",
        },
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    try:
        parameter_data = payload["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError("NASA POWER returned an invalid daily-data response") from exc

    columns: dict[str, pd.Series] = {}
    for api_name, column_name in POWER_PARAMETERS.items():
        records = parameter_data.get(api_name)
        if not isinstance(records, dict):
            raise TypeError(f"NASA POWER response is missing {api_name}")
        values = pd.Series(records, dtype=float)
        values.index = pd.to_datetime(values.index, format="%Y%m%d", errors="raise")
        columns[column_name] = values

    daily = pd.DataFrame(columns).sort_index()
    daily.index.name = "date"
    return clean_daily(daily)


def load_cell_daily(
    cell_id: str,
    refresh: bool = False,
    years: int = 20,
) -> pd.DataFrame:
    """Load a 20-year daily series from cache or fetch it from NASA POWER."""
    if years < 1:
        raise ValueError("years must be positive")
    path = get_cell_path(cell_id, "daily")
    end_date = date.today() - timedelta(days=1)
    start_date = end_date.replace(year=end_date.year - years)
    if os.path.exists(path) and not refresh:
        cached = _read_parquet(path)
        cache_start = pd.Timestamp(start_date)
        cache_end = pd.Timestamp(end_date - timedelta(days=30))
        if (
            not cached.empty
            and cached.index.min() <= cache_start
            and cached.index.max() >= cache_end
        ):
            return clean_daily(cached)
    if settings.demo_mode:
        raise ClimateDataUnavailable(
            f"No cached daily climate series is available for {cell_id} in demo mode"
        )

    lat, lon = cell_coordinates(cell_id)
    daily = fetch_power_daily(lat, lon, start_date, end_date)
    if daily.empty:
        raise RuntimeError(f"NASA POWER returned no daily observations for {cell_id}")
    _write_parquet_atomic(daily, path)
    return daily


def load_cell_weekly(
    cell_id: str,
    refresh: bool = False,
    years: int = 20,
) -> pd.DataFrame:
    """Load ISO weekly weather from cache, deriving it from daily data if needed."""
    path = get_cell_path(cell_id, "weekly")
    if os.path.exists(path) and not refresh:
        cached = pd.read_parquet(path)
        if isinstance(cached.index, pd.MultiIndex) and cached.index.names == ["year", "week"]:
            return cached.sort_index()

    weekly = to_weekly(load_cell_daily(cell_id, refresh=refresh, years=years))
    _write_parquet_atomic(weekly, path)
    return weekly


def _read_cached_normals(path: str) -> dict[str, list[float]]:
    frame = pd.read_parquet(path)
    if len(frame.index) != 52:
        raise RuntimeError(f"Cached climatology must contain 52 weeks: {path}")
    result = {column: frame[column].astype(float).tolist() for column in frame.columns}
    if "rain_mm" in result and "rain" not in result:
        result["rain"] = result["rain_mm"]
    return result


def load_cell_normals(
    cell_id: str,
    refresh: bool = False,
    years: int = 20,
) -> dict[str, list[float]]:
    """Load cached normals or compute them from the cell's NASA POWER daily series."""
    path = get_cell_path(cell_id, "normals")
    if os.path.exists(path) and not refresh:
        return _read_cached_normals(path)

    weekly = load_cell_weekly(cell_id, refresh=refresh, years=years)
    columns = [
        column
        for column in ("rain_mm", "tmean", "tmax", "ndvi")
        if column in weekly
    ]
    if not columns:
        raise RuntimeError(f"No supported NASA POWER variables are cached for {cell_id}")

    normals = weekly_normals(weekly, columns)
    values = normals_arrays(normals, columns)
    if "rain_mm" in values:
        values["rain"] = values["rain_mm"]
    frame = pd.DataFrame({key: value for key, value in values.items() if key != "rain"})
    frame.index = pd.RangeIndex(1, 53, name="week")
    _write_parquet_atomic(frame, path)
    return values


def load_cell_timeline(cell_id: str) -> dict:
    """Return 52-week normals and the latest complete available observed year."""
    try:
        normals = load_cell_normals(cell_id)
    except Exception as exc:
        logger.exception("Could not load climate normals for cell %s", cell_id)
        raise ClimateDataUnavailable(
            f"Climate normals are unavailable for cell {cell_id}"
        ) from exc

    try:
        weekly = load_cell_weekly(cell_id)
    except (OSError, RuntimeError, requests.RequestException) as exc:
        logger.warning(
            "Weekly observations unavailable for climate cell %s; serving cached normals",
            cell_id,
            exc_info=exc,
        )
        return {
            "normals": normals,
            "observations": {},
            "year": None,
        }

    if weekly.empty:
        return {"normals": normals, "observations": {}, "year": None}

    available_years = sorted(
        int(year) for year in weekly.index.get_level_values("year").unique()
    )
    complete_years = [
        year
        for year in available_years
        if set(range(1, 53)).issubset(
            set(
                int(week)
                for week in weekly.xs(year, level="year").index.tolist()
            )
        )
    ]
    year = complete_years[-1] if complete_years else available_years[-1]
    year_frame = weekly.xs(year, level="year").reindex(range(1, 53))
    observations: dict[str, list[float | None]] = {}
    for column in ("rain_mm", "tmean", "tmax", "ndvi"):
        if column not in year_frame:
            continue
        observations[column] = [
            float(value)
            if pd.notna(value) and math.isfinite(float(value))
            else None
            for value in year_frame[column].tolist()
        ]

    return {
        "normals": normals,
        "observations": observations,
        "year": year,
    }
