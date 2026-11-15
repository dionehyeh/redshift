import json
import math
from contextlib import contextmanager
from datetime import UTC, date, datetime

import pandas as pd
import pytest

from app.engine.scoring import soil_score
from app.errors import AppError
from app.services import (
    climate_service,
    earth_engine_service,
    field_service,
    scoring_service,
    soil_service,
    terrain_service,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeInfo:
    def __init__(self, value):
        self.value = value

    def getInfo(self):
        return self.value


class FakeSoilMoistureImage:
    def __init__(self, sample):
        self.sample = sample

    def reduceRegion(self, **_kwargs):
        return FakeInfo(self.sample["values"])

    def get(self, _key):
        return FakeInfo(self.sample["timestamp"])


class FakeSoilMoistureCollection:
    def __init__(self, sample):
        self.sample = sample

    def filterDate(self, *_args):
        return self

    def select(self, _bands):
        return self

    def sort(self, *_args):
        return self

    def first(self):
        if self.sample is None:
            return None
        return FakeSoilMoistureImage(self.sample)


class FakeEarthEngine:
    EEException = RuntimeError
    Geometry = type("Geometry", (), {"Point": staticmethod(lambda point: point)})
    Reducer = type("Reducer", (), {"first": staticmethod(lambda: "first")})

    def __init__(self, samples):
        self.samples = samples

    def ImageCollection(self, collection_id):
        return FakeSoilMoistureCollection(self.samples[collection_id])


def _soil_payload(values):
    return {
        "properties": {
            "layers": [
                {
                    "name": name,
                    "unit_measure": {"d_factor": 10},
                    "depths": [
                        {
                            "label": "0-5cm",
                            "values": {"mean": values.get(name)},
                        }
                    ],
                }
                for name in soil_service.SOIL_PROPERTIES
            ]
        }
    }


def test_soilgrids_profile_scales_values_and_estimates_texture(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params, timeout))
        return FakeResponse(
            _soil_payload(
                {
                    "phh2o": 55,
                    "soc": 378,
                    "clay": 317,
                    "sand": 450,
                    "silt": 233,
                }
            )
        )

    monkeypatch.setattr(soil_service.requests, "get", fake_get)

    result = soil_service.fetch_soil_profile(10.1, 76.4)

    assert result["soil_ph"] == 5.5
    assert result["soil_oc"] == 3.78
    assert result["clay_pct"] == 31.7
    assert result["soil_texture"] == "clay_loam"
    assert result["source"] == "ISRIC SoilGrids v2.0"
    assert calls[0][1]["property"] == list(soil_service.SOIL_PROPERTIES)


def test_soilgrids_missing_pixel_is_not_replaced_with_a_default(monkeypatch):
    monkeypatch.setattr(
        soil_service.requests,
        "get",
        lambda *args, **kwargs: FakeResponse(
            _soil_payload({property_name: None for property_name in soil_service.SOIL_PROPERTIES})
        ),
    )

    with pytest.raises(soil_service.SoilDataUnavailable):
        soil_service.fetch_soil_profile(9.5, 76.4)


def test_unclassified_soil_texture_is_reported_as_unknown():
    assert soil_service._texture_class(27, 20, 53) is None


@pytest.mark.parametrize(
    ("elevations", "expected_slope", "expected_flood"),
    [
        ([100 + 3 * (index % 7 - 3) for index in range(49)], 10.0, False),
        ([90 if index == 24 else 100 for index in range(49)], 0.0, True),
    ],
)
def test_srtm_profile_computes_slope_and_local_relief(
    monkeypatch,
    elevations,
    expected_slope,
    expected_flood,
):
    captured = {}

    def fake_get(url, params, timeout):
        captured.update(params)
        return FakeResponse(
            {
                "status": "OK",
                "results": [{"elevation": value} for value in elevations],
            }
        )

    monkeypatch.setattr(terrain_service.requests, "get", fake_get)

    result = terrain_service.fetch_terrain_profile(9.5, 76.4)

    assert len(captured["locations"].split("|")) == 49
    assert result["elevation_m"] == elevations[24]
    assert result["slope_pct"] == pytest.approx(expected_slope)
    assert result["flood_prone"] is expected_flood
    assert result["confidence"] == "low"


def test_modis_composite_is_only_applied_to_its_period_and_quality_filtered():
    start = date(2025, 1, 1)
    end = date(2025, 2, 2)
    good_timestamp = int(
        datetime(2025, 1, 1, tzinfo=UTC).timestamp() * 1000
    )
    cloudy_timestamp = int(
        datetime(2025, 1, 17, tzinfo=UTC).timestamp() * 1000
    )

    daily = earth_engine_service.modis_samples_to_daily(
        [
            {"timestamp": good_timestamp, "ndvi": 5000, "qa": 0},
            {"timestamp": cloudy_timestamp, "ndvi": 7000, "qa": 3},
        ],
        start,
        end,
    )

    assert daily[date(2025, 1, 1)] == 0.5
    assert daily[date(2025, 1, 16)] == 0.5
    assert daily[date(2025, 1, 17)] is None
    assert daily[date(2025, 2, 1)] is None


def test_imerg_week_is_omitted_below_coverage_threshold():
    weekly = earth_engine_service.imerg_features_to_weekly(
        [
            {
                "properties": {
                    "week": 1,
                    "rain_mm": 12.5,
                    "valid_intervals": 269,
                }
            },
            {
                "properties": {
                    "week": 2,
                    "rain_mm": 9.0,
                    "valid_intervals": 200,
                }
            },
            {
                "properties": {
                    "week": 3,
                    "rain_mm": 15.0,
                    "valid_intervals": float("inf"),
                }
            },
        ],
        2024,
    )

    assert weekly[1] == 12.5
    assert weekly[2] is None
    assert weekly[3] is None
    assert len(weekly) == 52


def test_imerg_folds_iso_week_53_into_week_52():
    weekly = earth_engine_service.imerg_features_to_weekly(
        [
            {
                "properties": {
                    "week": 52,
                    "rain_mm": 25.0,
                    "valid_intervals": 538,
                }
            }
        ],
        2020,
    )

    assert weekly[52] == 25.0
    assert len(weekly) == 52


def test_smap_rootzone_moisture_is_preferred_and_scaled_as_volume_fraction(monkeypatch):
    ee = FakeEarthEngine(
        {
            earth_engine_service.SMAP_COLLECTION: {
                "values": {"sm_rootzone": 0.24},
                "timestamp": 1_767_225_600_000,
            },
            earth_engine_service.GLDAS_COLLECTION: None,
        }
    )
    monkeypatch.setattr(earth_engine_service, "_earth_engine", lambda: ee)

    result = earth_engine_service.fetch_rootzone_soil_moisture(
        9.5, 76.4, as_of=date(2026, 1, 1)
    )

    assert result["sm_vol"] == 0.24
    assert result["source"] == "NASA SMAP L4 root-zone soil moisture"
    assert result["resolution"] == "9 km"
    assert result["observed_at"] == datetime.fromtimestamp(
        1_767_225_600, UTC
    ).isoformat()


def test_gldas_fills_smap_gap_using_top_metre_soil_water(monkeypatch):
    ee = FakeEarthEngine(
        {
            earth_engine_service.SMAP_COLLECTION: None,
            earth_engine_service.GLDAS_COLLECTION: {
                "values": {
                    "SoilMoi0_10cm_inst": 20,
                    "SoilMoi10_40cm_inst": 80,
                    "SoilMoi40_100cm_inst": 200,
                },
                "timestamp": 1_767_225_600_000,
            },
        }
    )
    monkeypatch.setattr(earth_engine_service, "_earth_engine", lambda: ee)

    result = earth_engine_service.fetch_rootzone_soil_moisture(
        9.5, 76.4, as_of=date(2026, 1, 1)
    )

    assert result["sm_vol"] == pytest.approx(0.3)
    assert result["source"] == "NASA GLDAS-2.1 Noah root-zone soil moisture"
    assert result["resolution"] == "28 km"


def test_point_soil_moisture_cache_avoids_repeated_provider_calls(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(climate_service.settings, "cache_dir", str(tmp_path))
    calls = []

    def fake_fetch(lat, lon, as_of):
        calls.append((lat, lon, as_of))
        return {
            "sm_vol": 0.2,
            "source": "NASA SMAP L4 root-zone soil moisture",
            "resolution": "9 km",
            "observed_at": "2026-01-01T00:00:00+00:00",
        }

    monkeypatch.setattr(climate_service, "fetch_rootzone_soil_moisture", fake_fetch)

    first = climate_service.load_point_soil_moisture(9.5, 76.4)
    second = climate_service.load_point_soil_moisture(9.5, 76.4)

    assert first["sm_vol"] == second["sm_vol"] == 0.2
    assert first["stale"] is False
    assert len(calls) == 1


def test_point_cache_snaps_ndvi_to_a_250_m_grid(tmp_path, monkeypatch):
    monkeypatch.setattr(climate_service.settings, "cache_dir", str(tmp_path))

    lat_step = 250 / 111_320
    lat = round(9.5 / lat_step) * lat_step + lat_step / 4
    lon_step = lat_step / max(math.cos(math.radians(lat)), 1e-6)
    lon = round(76.4 / lon_step) * lon_step + lon_step / 4
    first = climate_service.get_point_cache_path(lat, lon, "ndvi")
    nearby = climate_service.get_point_cache_path(
        lat,
        lon + lon_step / 20,
        "ndvi",
    )
    distant = climate_service.get_point_cache_path(lat, lon + lon_step * 3, "ndvi")

    assert first == nearby
    assert first != distant


def test_imerg_weekly_cache_is_point_and_year_specific(tmp_path, monkeypatch):
    monkeypatch.setattr(climate_service.settings, "cache_dir", str(tmp_path))
    expected = {week: float(week) if week != 7 else None for week in range(1, 53)}
    calls = []

    def fake_fetch(lat, lon, year):
        calls.append((lat, lon, year))
        return expected

    monkeypatch.setattr(climate_service, "fetch_imerg_weekly", fake_fetch)

    first = climate_service.load_point_imerg_weekly(9.5, 76.4, 2024)
    cached = climate_service.load_point_imerg_weekly(9.5, 76.4, 2024)

    assert first == expected
    assert cached == expected
    assert calls == [(9.5, 76.4, 2024)]


def test_field_timeline_prefers_imerg_and_uses_power_for_missing_weeks(monkeypatch):
    weekly = pd.DataFrame(
        {
            "rain_mm": [20.0] * 52,
            "tmean": [25.0] * 52,
            "tmax": [30.0] * 52,
        },
        index=pd.MultiIndex.from_tuples(
            [(2024, week) for week in range(1, 53)],
            names=["year", "week"],
        ),
    )
    imerg = {week: 10.0 for week in range(1, 53)}
    imerg[10] = None
    monkeypatch.setattr(
        climate_service,
        "load_cell_normals",
        lambda _cell_id, point=None: {
            "rain_mm": [20.0] * 52,
            "rain": [20.0] * 52,
            "tmean": [25.0] * 52,
            "tmax": [30.0] * 52,
        },
    )
    monkeypatch.setattr(
        climate_service,
        "load_cell_weekly",
        lambda _cell_id, point=None: weekly,
    )
    monkeypatch.setattr(
        climate_service,
        "load_point_imerg_weekly",
        lambda lat, lon, year: imerg,
    )

    result = climate_service.load_cell_timeline(
        "09.5N_076.5E",
        point=(9.5, 76.4),
    )

    assert result["observations"]["rain_mm"][0] == 10.0
    assert result["observations"]["rain_mm"][9] == 20.0
    assert result["observation_sources"]["rain_mm"].startswith("NASA GPM IMERG")


class FakeCursor:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, field):
        self.field = field
        self.statements = []

    def execute(self, query, params=()):
        self.statements.append((query, params))
        if query.startswith("SELECT * FROM fields"):
            return FakeCursor(self.field)
        return FakeCursor()


@pytest.fixture
def onboard_field(monkeypatch):
    field = {
        "id": 41,
        "lat": 10.1,
        "lon": 76.4,
        "water_source": "rainfed",
        "water_quality": "unknown",
    }
    connection = FakeConnection(field)

    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(field_service, "get_db", fake_get_db)
    monkeypatch.setattr(field_service, "update_job_step", lambda *args: None)
    monkeypatch.setattr(field_service, "load_cell_normals", lambda _cell: {
        "rain_mm": [10.0] * 52,
        "tmean": [25.0] * 52,
        "tmax": [30.0] * 52,
    })
    monkeypatch.setattr(
        field_service,
        "load_crops",
        lambda: [{"name": "rice", "start_windows": [(1, 12)]}],
    )
    monkeypatch.setattr(
        field_service,
        "hard_filter",
        lambda *args: ("suitable", []),
    )
    completed = []
    monkeypatch.setattr(
        field_service,
        "complete_job",
        lambda *args: completed.append(args),
    )
    monkeypatch.setattr(
        field_service,
        "fail_job",
        lambda *args: pytest.fail(f"unexpected job failure: {args}"),
    )

    return connection, completed


def _profile_update(connection):
    params = next(
        params
        for query, params in connection.statements
        if query.startswith("UPDATE fields SET") and "profile_meta = ?" in query
    )
    return params, json.loads(params[-2])


def test_field_onboarding_persists_live_terrain_and_soil_values(
    onboard_field,
    monkeypatch,
):
    connection, completed = onboard_field
    monkeypatch.setattr(
        field_service,
        "fetch_terrain_profile",
        lambda lat, lon: {
            "elevation_m": 18.5,
            "slope": "moderate",
            "slope_pct": 4.0,
            "relative_elevation_m": -1.0,
            "flood_prone": False,
            "source": "SRTM GL1 via OpenTopoData",
            "confidence": "low",
        },
    )
    monkeypatch.setattr(
        field_service,
        "fetch_soil_profile",
        lambda lat, lon: {
            "soil_ph": 6.2,
            "soil_oc": 2.4,
            "soil_texture": "loam",
            "clay_pct": 24.0,
            "sand_pct": 40.0,
            "silt_pct": 36.0,
            "source": "ISRIC SoilGrids v2.0",
            "confidence": "medium",
        },
    )

    field_service.onboard_field_task("job-41", 41)

    params, metadata = _profile_update(connection)
    assert params[0] == "ready"
    assert params[2] == 18.5
    assert params[6] == 6.2
    assert metadata["elevation_m"]["value"] == 18.5
    assert metadata["soil_ph"]["value"] == 6.2
    assert completed[0][1] == "done"


def test_field_onboarding_reports_partial_soilgrids_properties(
    onboard_field,
    monkeypatch,
):
    connection, completed = onboard_field
    monkeypatch.setattr(
        field_service,
        "fetch_terrain_profile",
        lambda lat, lon: {
            "elevation_m": 18.5,
            "slope": "moderate",
            "slope_pct": 4.0,
            "relative_elevation_m": -1.0,
            "flood_prone": False,
            "source": "SRTM GL1 via OpenTopoData",
            "confidence": "low",
        },
    )
    monkeypatch.setattr(
        field_service,
        "fetch_soil_profile",
        lambda lat, lon: {
            "soil_ph": 6.2,
            "soil_oc": None,
            "soil_texture": None,
            "clay_pct": 24.0,
            "sand_pct": 40.0,
            "silt_pct": 36.0,
            "source": "ISRIC SoilGrids v2.0",
            "confidence": "medium",
        },
    )

    field_service.onboard_field_task("job-41", 41)

    params, metadata = _profile_update(connection)
    assert params[0] == "ready"
    assert metadata["soil_oc"]["value"] is None
    assert "SoilGrids soil properties are incomplete" in metadata["gaps"]
    assert completed[0][1] == "done_with_gaps"


def test_field_onboarding_does_not_score_with_missing_elevation(
    onboard_field,
    monkeypatch,
):
    connection, completed = onboard_field
    monkeypatch.setattr(
        field_service,
        "fetch_terrain_profile",
        lambda lat, lon: fail_terrain_lookup(),
    )
    monkeypatch.setattr(
        field_service,
        "fetch_soil_profile",
        lambda lat, lon: {
            "soil_ph": 6.2,
            "soil_oc": 2.4,
            "soil_texture": "loam",
            "clay_pct": 24.0,
            "sand_pct": 40.0,
            "silt_pct": 36.0,
            "source": "ISRIC SoilGrids v2.0",
            "confidence": "medium",
        },
    )

    field_service.onboard_field_task("job-41", 41)

    params, metadata = _profile_update(connection)
    assert params[0] == "failed"
    assert params[2] is None
    assert metadata["elevation_m"]["value"] is None
    assert "SRTM terrain profile is unavailable" in metadata["gaps"]
    assert not any("INSERT INTO field_crops" in query for query, _ in connection.statements)
    assert completed[0][1] == "done_with_gaps"


def test_scoring_rejects_missing_live_inputs_instead_of_using_demo_constants():
    with pytest.raises(AppError) as error:
        scoring_service.build_scoring_environment(
            {"elevation_m": None, "climate_cell_id": "09.5N_076.5E"},
            [],
            2,
            24,
        )

    assert error.value.code == "FIELD_PROFILE_INCOMPLETE"


def test_valid_scoring_environment_preserves_unknown_soil_values(monkeypatch):
    monkeypatch.setattr(
        scoring_service,
        "load_cell_normals",
        lambda _cell: {
            "rain": [10.0] * 52,
            "tmean": [25.0] * 52,
            "tmax": [30.0] * 52,
        },
    )

    env = scoring_service.build_scoring_environment(
        {
            "climate_cell_id": "09.5N_076.5E",
            "elevation_m": 18.5,
            "flood_prone": None,
            "drainage": None,
            "soil_ph": None,
            "water_source": "unknown",
            "water_quality": "unknown",
        },
        [],
        2,
        24,
    )

    assert env["field"]["elevation_m"] == 18.5
    assert env["field"]["ph"] is None
    assert env["field"]["drainage"] is None


def test_scoring_uses_satellite_soil_moisture_when_farmer_answer_is_missing(
    monkeypatch,
):
    monkeypatch.setattr(
        scoring_service,
        "load_cell_normals",
        lambda _cell: {
            "rain": [10.0] * 52,
            "tmean": [25.0] * 52,
            "tmax": [30.0] * 52,
        },
    )
    monkeypatch.setattr(
        scoring_service,
        "load_point_soil_moisture",
        lambda *_args: {
            "sm_vol": 0.25,
            "source": "NASA SMAP L4 root-zone soil moisture",
            "resolution": "9 km",
            "observed_at": "2026-01-01T00:00:00+00:00",
            "stale": False,
        },
    )

    env = scoring_service.build_scoring_environment(
        {
            "id": 7,
            "lat": 9.5,
            "lon": 76.4,
            "climate_cell_id": "09.5N_076.5E",
            "elevation_m": 18.5,
        },
        [],
        2,
        24,
    )

    assert env["stored_mm"] == 90.0
    assert env["stored_water"]["source"] == "NASA SMAP L4 root-zone soil moisture"
    assert env["stored_water"]["confidence"] == "medium"
    assert env["source_gaps"] == []


def test_scoring_reports_soil_moisture_gap_when_smap_and_gldas_are_unavailable(
    monkeypatch,
):
    monkeypatch.setattr(
        scoring_service,
        "load_cell_normals",
        lambda _cell: {
            "rain": [10.0] * 52,
            "tmean": [25.0] * 52,
            "tmax": [30.0] * 52,
        },
    )

    def unavailable(*_args):
        raise earth_engine_service.EarthObservationDataUnavailable(
            "providers unavailable"
        )

    monkeypatch.setattr(scoring_service, "load_point_soil_moisture", unavailable)

    env = scoring_service.build_scoring_environment(
        {
            "id": 7,
            "lat": 9.5,
            "lon": 76.4,
            "climate_cell_id": "09.5N_076.5E",
            "elevation_m": 18.5,
        },
        [],
        2,
        24,
    )

    assert env["stored_mm"] == 45.0
    assert env["stored_water"]["confidence"] == "low"
    assert "SMAP and GLDAS" in env["source_gaps"][0]


def test_scoring_uses_transparent_climatology_when_no_current_outlook(monkeypatch):
    monkeypatch.setattr(
        scoring_service,
        "load_cell_normals",
        lambda _cell: {
            "rain": [10.0] * 52,
            "tmean": [25.0] * 52,
            "tmax": [30.0] * 52,
        },
    )

    def no_current_outlook():
        raise AppError(
            "OUTLOOK_UNAVAILABLE",
            "No current seasonal outlook",
            status=503,
        )

    monkeypatch.setattr(
        scoring_service, "get_seasonal_outlook", no_current_outlook
    )
    env = scoring_service.build_scoring_environment(
        {
            "climate_cell_id": "09.5N_076.5E",
            "elevation_m": 18.5,
        },
        [],
        2,
        24,
    )

    assert env["outlook_info"]["forecast_available"] is False
    assert env["outlook_info"]["factor_range"] == [0.85, 1.15]
    assert env["outlook_info"]["confidence"] == "low"
    assert env["outlook_info"]["source_gap"]
    assert env["outlook_factor"] == 1.0


def test_scoring_uses_the_current_bulletin_factor_range(monkeypatch):
    monkeypatch.setattr(
        scoring_service,
        "load_cell_normals",
        lambda _cell: {
            "rain": [10.0] * 52,
            "tmean": [25.0] * 52,
            "tmax": [30.0] * 52,
        },
    )
    monkeypatch.setattr(
        scoring_service,
        "get_seasonal_outlook",
        lambda: {
            "factor_range": [0.8, 0.9],
            "source": "IMD bulletin",
            "valid_for": "2026 monsoon",
            "entered_on": "2026-05-01",
        },
    )

    env = scoring_service.build_scoring_environment(
        {"climate_cell_id": "09.5N_076.5E", "elevation_m": 18.5},
        [],
        2,
        24,
    )

    assert env["outlook_factor"] == 0.85
    assert env["outlook_info"]["forecast_available"] is True
    assert env["outlook_info"]["source"] == "IMD bulletin"


def test_unknown_slope_does_not_receive_erosion_cover_score_bonus():
    crop = {
        "ph_min": 5.5,
        "ph_max": 6.5,
        "waterlog_tol": "M",
        "n_effect": "neutral",
        "om_bonus": False,
        "erosion_cover": True,
        "duration_days": 90,
    }
    unknown = {"ph": None, "drainage": None, "flood_prone": None, "slope": None}
    low_slope = {**unknown, "slope": "low"}
    zero_ph = {**low_slope, "ph": 0}

    assert soil_score(crop, unknown, 0) == soil_score(crop, low_slope, 0)
    assert soil_score(crop, zero_ph, 0) < soil_score(crop, unknown, 0)


def fail_terrain_lookup():
    raise terrain_service.TerrainDataUnavailable("offline")
