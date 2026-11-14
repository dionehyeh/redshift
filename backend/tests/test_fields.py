import json
from contextlib import contextmanager

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import current_user
from app.errors import register_error_handlers
from app.routers import fields as fields_router
from app.services import climate_service

USER = {
    "id": 7,
    "role": "farmer",
    "name": "Test Farmer",
    "language": "en",
    "contact": "farmer@example.test",
}

FIELD = {
    "id": 41,
    "farmer_id": 7,
    "name": "North Plot",
    "lat": 9.5,
    "lon": 76.4,
    "area_ha": 1.2,
    "water_source": "rainfed",
    "water_quality": "good",
    "profile_status": "ready",
    "climate_cell_id": "09.5N_076.5E",
    "created_at": "2026-01-01",
    "profile_meta": None,
    "soil_ph": None,
    "soil_oc": None,
    "soil_texture": None,
    "elevation_m": None,
    "slope": None,
    "flood_prone": None,
    "drainage": None,
    "boundary_geojson": None,
}


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.statements = []

    def execute(self, query, params=()):
        self.statements.append((query, params))
        if "INSERT INTO fields" in query:
            return FakeCursor({"id": FIELD["id"]})
        if "INSERT INTO jobs" in query:
            return FakeCursor()
        if "SELECT id, name, lat, lon" in query:
            return FakeCursor(
                rows=[
                    {
                        "id": FIELD["id"],
                        "name": FIELD["name"],
                        "lat": FIELD["lat"],
                        "lon": FIELD["lon"],
                        "area_ha": FIELD["area_ha"],
                        "profile_status": FIELD["profile_status"],
                        "climate_cell_id": FIELD["climate_cell_id"],
                        "water_source": FIELD["water_source"],
                        "created_at": FIELD["created_at"],
                    }
                ]
            )
        if "FROM field_crops fc" in query:
            return FakeCursor(
                rows=[
                    {
                        "crop_id": 1,
                        "crop_class": "suitable",
                        "reason": "Conditions met",
                        "start_windows": "1-12;30-40",
                        "computed_at": "2026-01-01",
                        "name": "paddy",
                        "name_ml": "നെല്ല്",
                        "duration_days": 120,
                        "water_need": "high",
                        "family": "Poaceae",
                    },
                    {
                        "crop_id": 2,
                        "crop_class": "marginal",
                        "reason": "Short overlap",
                        "start_windows": "",
                        "computed_at": "2026-01-01",
                        "name": "cowpea",
                        "name_ml": None,
                        "duration_days": 90,
                        "water_need": "low",
                        "family": "Fabaceae",
                    },
                ]
            )
        if "FROM seasons s" in query:
            return FakeCursor(rows=[])
        return FakeCursor()


@pytest.fixture
def field_client(monkeypatch):
    connection = FakeConnection()
    field_state = dict(FIELD)

    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(fields_router, "get_db", fake_get_db, raising=False)
    monkeypatch.setattr(fields_router, "onboard_field_task", lambda *args: None)
    monkeypatch.setattr(
        fields_router,
        "load_cell_timeline",
        lambda _cell_id, point=None: {
            "normals": {
                "rain": [10, 20],
                "tmean": [25] * 53,
                "tmax": [30] * 52,
            },
            "observations": {},
            "year": None,
        },
    )

    service = __import__("app.services.field_service", fromlist=["get_db"])
    monkeypatch.setattr(service, "get_db", fake_get_db)

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(fields_router.router, prefix="/api/v1")
    app.dependency_overrides[current_user] = lambda: USER
    app.dependency_overrides[fields_router.get_owned_field] = lambda id: dict(field_state)

    with TestClient(app) as client:
        yield client, connection, field_state


def test_create_field_returns_accepted_job(field_client):
    client, connection, _ = field_client

    response = client.post(
        "/api/v1/fields",
        json={
            "name": "North Plot",
            "lat": 9.5,
            "lon": 76.4,
            "water_source": "rainfed",
            "water_quality": "good",
            "area_ha": 1.2,
        },
    )

    assert response.status_code == 202
    assert response.json() == {
        "field_id": 41,
        "job_id": "job_field_41",
        "status": "queued",
    }
    assert any("INSERT INTO fields" in query for query, _ in connection.statements)
    assert any("INSERT INTO jobs" in query for query, _ in connection.statements)


def test_field_list_returns_profile_readiness(field_client):
    client, _, _ = field_client

    response = client.get("/api/v1/fields?status=ready")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["profile_status"] == "ready"


def test_field_profile_and_feasible_crop_groups(field_client):
    client, _, _ = field_client

    profile = client.get("/api/v1/fields/41")
    feasible = client.get("/api/v1/fields/41/feasible-crops")

    assert profile.status_code == 200
    assert profile.json()["profile"]["soil_ph"]["value"] is None
    assert feasible.status_code == 200
    assert feasible.json()["suitable"][0]["crop_name"] == "paddy"
    assert feasible.json()["marginal"][0]["crop_name"] == "cowpea"


def test_feasible_crops_requires_ready_field(field_client):
    client, _, field_state = field_client
    field_state["profile_status"] = "building"

    response = client.get("/api/v1/fields/41/feasible-crops")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FIELD_NOT_READY"


def test_timeline_has_exactly_52_weeks_without_fabricating_ndvi(field_client):
    client, _, _ = field_client

    response = client.get("/api/v1/fields/41/timeline")
    data = response.json()

    assert response.status_code == 200
    assert len(data["weeks"]) == 52
    assert len(data["normals"]["rain_mm"]) == 52
    assert data["normals"]["rain_mm"][:3] == [10, 20, None]
    assert data["normals"]["tmean"][-1] == 25
    assert "ndvi" not in data["series"]
    assert "no historical weekly observations" in data["source_note"]


def test_timeline_prefers_historical_observations_and_retains_normals(
    field_client, monkeypatch
):
    client, _, _ = field_client
    monkeypatch.setattr(
        fields_router,
        "load_cell_timeline",
        lambda _cell_id, point=None: {
            "normals": {"rain_mm": [12.0] * 52, "tmean": [25.0] * 52},
            "observations": {
                "rain_mm": [18.0] * 52,
                "tmean": [27.0] * 52,
                "ndvi": [0.4] * 52,
            },
            "year": 2025,
        },
    )

    response = client.get("/api/v1/fields/41/timeline")
    data = response.json()

    assert response.status_code == 200
    assert data["series"]["rain_mm"]["values"] == [18.0] * 52
    assert data["series"]["rain_mm"]["is_normal"] is False
    assert data["normals"]["rain_mm"] == [12.0] * 52
    assert data["series"]["ndvi"]["values"] == [0.4] * 52
    assert "2025" in data["source_note"]


def test_map_without_boundary_only_returns_recorded_point(field_client):
    client, _, _ = field_client

    response = client.get("/api/v1/fields/41/map")

    assert response.status_code == 200
    features = response.json()["features"]
    assert len(features) == 1
    assert features[0]["geometry"] == {
        "type": "Point",
        "coordinates": [76.4, 9.5],
    }


def test_history_is_field_scoped(field_client):
    client, connection, _ = field_client

    response = client.get("/api/v1/fields/41/history")

    assert response.status_code == 200
    assert response.json() == {"field_id": 41, "total": 0, "seasons": []}
    assert any("WHERE s.field_id = ?" in query for query, _ in connection.statements)


def test_patch_records_soil_correction_and_updates_profile_metadata(field_client):
    client, connection, _ = field_client

    response = client.patch(
        "/api/v1/fields/41",
        json={
            "water_source": "canal",
            "corrections": [{"key": "soil_ph", "value": 6.1}],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "updated",
        "field_id": 41,
        "job_id": None,
    }
    insert = next(
        (query, params)
        for query, params in connection.statements
        if "INSERT INTO corrections" in query
    )
    assert insert[1][1:4] == (7, "soil_ph", "Farmer correction: 6.1")
    update = next(
        (query, params)
        for query, params in connection.statements
        if query.startswith("UPDATE fields SET")
    )
    metadata = json.loads(update[1][-2])
    assert metadata["soil_ph"]["value"] == 6.1
    assert metadata["water_source"]["value"] == "canal"


def test_coordinate_patch_queues_profile_rebuild(field_client):
    client, connection, _ = field_client

    response = client.patch("/api/v1/fields/41", json={"lat": 10.1})

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["job_id"].startswith("job_field_41_")
    assert any("INSERT INTO jobs" in query for query, _ in connection.statements)


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "No coordinates", "lat": None, "lon": 76.4},
        {"name": "Out of range", "lat": 91, "lon": 76.4},
        {"name": "Bad boundary", "lat": 9.5, "lon": 76.4, "boundary_geojson": "not-json"},
    ],
)
def test_create_validates_field_input(field_client, payload):
    client, _, _ = field_client
    request = {
        "name": payload.get("name", "Valid Plot"),
        "lat": payload.get("lat", 9.5),
        "lon": payload.get("lon", 76.4),
    }
    request.update(payload)

    response = client.post("/api/v1/fields", json=request)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"


def test_patch_rejects_empty_or_unknown_soil_correction(field_client):
    client, _, _ = field_client

    empty_response = client.patch("/api/v1/fields/41", json={})
    invalid_correction_response = client.patch(
        "/api/v1/fields/41",
        json={"corrections": [{"key": "elevation_m", "value": 10}]},
    )

    assert empty_response.status_code == 422
    assert invalid_correction_response.status_code == 422


def test_climate_service_selects_latest_complete_observed_year(monkeypatch):
    index = pd.MultiIndex.from_tuples(
        [(year, week) for year, weeks in ((2024, range(1, 53)), (2025, range(1, 10))) for week in weeks],
        names=["year", "week"],
    )
    weekly = pd.DataFrame(
        {
            "rain_mm": [float(week) for _, week in index],
            "tmean": [25.0] * len(index),
            "tmax": [30.0] * len(index),
        },
        index=index,
    )
    monkeypatch.setattr(
        climate_service,
        "load_cell_normals",
        lambda _cell_id: {"rain_mm": [12.0] * 52, "tmean": [26.0] * 52},
    )
    monkeypatch.setattr(climate_service, "load_cell_weekly", lambda _cell_id: weekly)

    result = climate_service.load_cell_timeline("09.5N_076.5E")

    assert result["year"] == 2024
    assert len(result["observations"]["rain_mm"]) == 52
    assert result["observations"]["rain_mm"][0] == 1.0
    assert result["observations"]["rain_mm"][-1] == 52.0
