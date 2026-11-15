from datetime import date
from unittest.mock import Mock, patch

import numpy as np
import pytest

from app.config import settings
from app.services.climate_service import (
    ClimateDataUnavailable,
    cell_coordinates,
    fetch_power_daily,
    get_cell_path,
    grid_cell_id,
    load_cell_daily,
)


def test_grid_cell_id_rounds_to_power_grid_and_parses_hemispheres():
    cell_id = grid_cell_id(9.49, 76.4)
    assert cell_id == "09.5N_076.5E"
    assert cell_coordinates(cell_id) == (9.5, 76.5)
    assert cell_coordinates(grid_cell_id(-9.6, -76.6)) == (-9.5, -76.5)
    assert cell_coordinates(grid_cell_id(9.25, -9.25)) == (9.5, -9.5)


def test_grid_cell_id_rejects_out_of_range_coordinates():
    with pytest.raises(ValueError):
        grid_cell_id(91, 0)
    with pytest.raises(ValueError):
        cell_coordinates("99.0N_076.5E")


def test_get_cell_path_rejects_path_components(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    with pytest.raises(ValueError):
        get_cell_path("../outside")


def test_demo_mode_never_fetches_uncached_daily_data(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "cache_dir", str(tmp_path))
    monkeypatch.setattr(settings, "demo_mode", True)
    with (
        patch("app.services.climate_service.requests.get") as get,
        pytest.raises(ClimateDataUnavailable),
    ):
        load_cell_daily("09.5N_076.5E")
    get.assert_not_called()


@patch("app.services.climate_service.requests.get")
def test_fetch_power_daily_maps_missing_flags_and_clips_rain(get):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "properties": {
            "parameter": {
                "PRECTOTCORR": {"20240101": -999, "20240102": -3},
                "T2M": {"20240101": -9999, "20240102": 28.5},
                "T2M_MAX": {"20240101": 31.0, "20240102": 32.0},
            }
        }
    }
    get.return_value = response

    daily = fetch_power_daily(9.5, 76.5, date(2024, 1, 1), date(2024, 1, 2))
    assert np.isnan(daily["rain_mm"].iloc[0])
    assert daily["rain_mm"].iloc[1] == 0
    assert np.isnan(daily["tmean"].iloc[0])
    assert daily["tmax"].tolist() == [31.0, 32.0]
    assert get.call_args.kwargs["params"]["parameters"] == "PRECTOTCORR,T2M,T2M_MAX"
