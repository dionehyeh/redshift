from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import deps
from app.errors import register_error_handlers
from app.routers import seasons


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, *, crop=None, job=None, findings=None):
        self.crop = crop
        self.job = job
        self.findings = findings or []
        self.statements = []

    def execute(self, query, params=()):
        self.statements.append((query, params))
        if "SELECT id, name FROM crops" in query:
            return FakeCursor(self.crop)
        if "SELECT id FROM crops" in query:
            return FakeCursor(self.crop)
        if "INSERT INTO seasons" in query:
            return FakeCursor({"id": 31})
        if "FROM jobs" in query and "season_analysis" in query:
            return FakeCursor(self.job)
        if "FROM findings" in query:
            return FakeCursor(rows=self.findings)
        return FakeCursor()


FARMER = {"id": 7, "role": "farmer"}
SEASON = {
    "id": 31,
    "field_id": 12,
    "crop_id": 2,
    "crop_name": "paddy",
    "status": "completed",
    "start_date": "2025-06-01",
    "end_date": "2025-10-15",
    "outcome": "poor",
    "loss_percent": 30,
    "suspected_cause": "water_shortage",
    "investment": 1000,
    "revenue": 500,
    "approval_status": "pending_review",
    "approved_cause": None,
    "approver_role": None,
}


def create_client(monkeypatch, connection, season=SEASON, finding=None):
    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(seasons, "get_db", fake_get_db)
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(seasons.router, prefix="/api/v1")
    app.dependency_overrides[deps.current_user] = lambda: dict(FARMER)
    app.dependency_overrides[deps.own_field] = lambda: {"id": 12, "farmer_id": 7}
    app.dependency_overrides[deps.own_season] = lambda: dict(season)
    if finding:
        app.dependency_overrides[deps.reviewable_finding] = lambda: dict(finding)
    return TestClient(app)


def test_log_season_requires_a_known_crop_and_stores_the_full_record(monkeypatch):
    connection = FakeConnection(crop={"id": 2, "name": "Paddy"})
    client = create_client(monkeypatch, connection)

    response = client.post(
        "/api/v1/fields/12/seasons",
        json={
            "crop": "paddy",
            "start_date": "2025-06-01",
            "end_date": "2025-10-15",
            "outcome": "poor",
            "loss_percent": 30,
            "investment": 1000,
            "revenue": 500,
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 31,
        "field_id": 12,
        "status": "completed",
        "crop": "Paddy",
        "approval_status": "pending_review",
    }
    query, params = next(
        (query, params)
        for query, params in connection.statements
        if "INSERT INTO seasons" in query
    )
    assert "investment, revenue" in query
    assert params == (
        12,
        2,
        "2025-06-01",
        "2025-10-15",
        "poor",
        30,
        None,
        1000.0,
        500.0,
    )


def test_log_season_rejects_unknown_crops_without_creating_records(monkeypatch):
    connection = FakeConnection()
    client = create_client(monkeypatch, connection)

    response = client.post(
        "/api/v1/fields/12/seasons",
        json={
            "crop": "unknown crop",
            "start_date": "2025-06-01",
            "end_date": "2025-10-15",
            "outcome": "good",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"
    assert not any("INSERT INTO seasons" in query for query, _ in connection.statements)


def test_season_create_validates_dates_finances_and_loss_values(monkeypatch):
    client = create_client(monkeypatch, FakeConnection(crop={"id": 2, "name": "Paddy"}))

    invalid_requests = [
        {
            "crop": "paddy",
            "start_date": "2025-10-15",
            "end_date": "2025-06-01",
            "outcome": "good",
        },
        {
            "crop": "paddy",
            "start_date": "2025-06-01",
            "end_date": "2025-10-15",
            "outcome": "good",
            "investment": -1,
        },
        {
            "crop": "paddy",
            "start_date": "2025-06-01",
            "end_date": "2025-10-15",
            "outcome": "good",
            "loss_percent": 101,
        },
    ]

    for payload in invalid_requests:
        response = client.post("/api/v1/fields/12/seasons", json=payload)
        assert response.status_code == 422


def test_patch_season_updates_dates_outcome_and_finances(monkeypatch):
    connection = FakeConnection()
    client = create_client(monkeypatch, connection)

    response = client.patch(
        "/api/v1/seasons/31",
        json={
            "start_date": "2025-06-03",
            "end_date": "2025-10-20",
            "outcome": "average",
            "investment": 1200,
            "revenue": 2400,
        },
    )

    assert response.status_code == 200
    assert response.json() == {"status": "updated", "id": 31}
    query, params = next(
        (query, params)
        for query, params in connection.statements
        if "UPDATE seasons SET" in query
    )
    assert "start_date = ?" in query
    assert "end_date = ?" in query
    assert "outcome = ?" in query
    assert "investment = ?" in query
    assert "revenue = ?" in query
    assert params[-1] == 31


def test_patch_season_validates_dates_against_existing_values(monkeypatch):
    connection = FakeConnection()
    client = create_client(monkeypatch, connection)

    response = client.patch(
        "/api/v1/seasons/31",
        json={"end_date": "2025-05-31"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION"
    assert not any("UPDATE seasons SET" in query for query, _ in connection.statements)


def test_get_season_returns_crop_and_review_status(monkeypatch):
    client = create_client(monkeypatch, FakeConnection())

    response = client.get("/api/v1/seasons/31")

    assert response.status_code == 200
    data = response.json()
    assert data["crop"] == "paddy"
    assert data["outcome"] == "poor"
    assert data["investment"] == 1000
    assert data["approval_status"] == "pending_review"


def test_analysis_not_started_has_no_assumed_observations(monkeypatch):
    connection = FakeConnection()
    client = create_client(monkeypatch, connection)

    response = client.get("/api/v1/seasons/31/analysis")

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_status"] == "not_started"
    assert data["job_id"] is None
    assert data["findings"] == []
    assert data["gaps"] == []
    assert data["comparison_years"] is None
    assert data["likely_causes"] is None


def test_analyze_season_enqueues_background_work(monkeypatch):
    connection = FakeConnection()
    client = create_client(monkeypatch, connection)
    jobs = []
    tasks = []
    monkeypatch.setattr(
        seasons,
        "create_job",
        lambda job_id, kind, target_id, steps: jobs.append(
            (job_id, kind, target_id, steps)
        ),
    )
    monkeypatch.setattr(
        seasons,
        "analyze_season_task",
        lambda job_id, season_id: tasks.append((job_id, season_id)),
    )

    response = client.post("/api/v1/seasons/31/analyze")

    assert response.status_code == 202
    result = response.json()
    assert result["season_id"] == 31
    assert result["status"] == "queued"
    assert jobs == [
        (
            result["job_id"],
            "season_analysis",
            31,
            [
                "loading_season",
                "calculating_anomalies",
                "synthesizing_stress_flags",
            ],
        )
    ]
    assert tasks == [(result["job_id"], 31)]


def test_analysis_waiting_state_contains_no_fabricated_findings_or_gaps(monkeypatch):
    connection = FakeConnection(
        job={"id": "job-1", "status": "running", "result_json": None, "error": None},
        findings=[
            {
                "id": 80,
                "kind": "heat",
                "week_from": 10,
                "week_to": 11,
                "deviation": 2,
                "unit": "°C",
                "crop_stage": "flowering",
                "severity": "2",
                "confidence": "medium",
                "source": "NASA POWER",
                "resolution": "~50 km",
                "text_plain": "Heat stress",
                "explainer_key": None,
                "review_status": "pending",
            }
        ],
    )
    client = create_client(monkeypatch, connection)

    response = client.get("/api/v1/seasons/31/analysis")

    assert response.status_code == 200
    assert response.json() == {
        "season_id": 31,
        "approval_status": "pending_review",
        "analysis_status": "running",
        "job_id": "job-1",
        "comparison_years": None,
        "findings": [],
        "gaps": [],
        "likely_causes": None,
        "followup_question": None,
        "analysis_error": None,
    }
    assert not any("FROM findings" in query for query, _ in connection.statements)


def test_completed_analysis_returns_stored_period_causes_gaps_and_findings(monkeypatch):
    connection = FakeConnection(
        job={
            "id": "job-2",
            "status": "done_with_gaps",
            "result_json": (
                '{"comparison_years":"2010-2021 (12-year climatology)",'
                '"finding_ids":[81],'
                '"gaps":["NDVI unavailable"],'
                '"likely_causes":{"suspected":[{"cause":"heat_stress"}]}}'
            ),
            "error": None,
        },
        findings=[
            {
                "id": 81,
                "kind": "heat",
                "week_from": 10,
                "week_to": 11,
                "deviation": 2,
                "unit": "°C",
                "crop_stage": "flowering",
                "severity": "2",
                "confidence": "medium",
                "source": "NASA POWER",
                "resolution": "~50 km",
                "text_plain": "Heat stress",
                "explainer_key": "normals",
                "review_status": "pending",
            },
            {
                "id": 82,
                "kind": "rain_deficit",
                "week_from": 4,
                "week_to": 5,
                "deviation": 20,
                "unit": "%",
                "crop_stage": "vegetative",
                "severity": "4",
                "confidence": "high",
                "source": "NASA POWER",
                "resolution": "~50 km",
                "text_plain": "Earlier finding from an older analysis",
                "explainer_key": None,
                "review_status": "confirmed",
            },
        ],
    )
    client = create_client(monkeypatch, connection)

    response = client.get("/api/v1/seasons/31/analysis")

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_status"] == "done_with_gaps"
    assert data["comparison_years"] == "2010-2021 (12-year climatology)"
    assert data["gaps"] == ["NDVI unavailable"]
    assert data["likely_causes"] == {"suspected": [{"cause": "heat_stress"}]}
    assert data["findings"][0]["deviation"] == "2°C"
    assert data["findings"][0]["unit"] == "°C"
    assert [finding["id"] for finding in data["findings"]] == [81]
    assert data["followup_question"]


def test_analysis_failed_state_returns_error_without_old_findings(monkeypatch):
    connection = FakeConnection(
        job={
            "id": "job-3",
            "status": "failed",
            "result_json": None,
            "error": "Season analysis failed",
        }
    )
    client = create_client(monkeypatch, connection)

    response = client.get("/api/v1/seasons/31/analysis")

    assert response.status_code == 200
    assert response.json()["analysis_status"] == "failed"
    assert response.json()["analysis_error"] == "Season analysis failed"
    assert response.json()["findings"] == []


def test_confirming_a_finding_uses_its_diagnosed_cause(monkeypatch):
    connection = FakeConnection()
    client = create_client(
        monkeypatch,
        connection,
        finding={
            "id": 81,
            "season_id": 31,
            "kind": "heat",
        },
    )

    response = client.post(
        "/api/v1/findings/81/review",
        json={"action": "confirm"},
    )

    assert response.status_code == 200
    assert response.json()["approved_cause"] == "heat_stress"
    correction = next(
        params
        for query, params in connection.statements
        if "INSERT INTO corrections" in query
    )
    assert correction[3] == "heat_stress"
    approval = next(
        params
        for query, params in connection.statements
        if "UPDATE seasons" in query
    )
    assert approval[0:2] == ("heat_stress", "approved")


def test_correcting_a_finding_requires_and_persists_the_corrected_cause(monkeypatch):
    connection = FakeConnection()
    client = create_client(
        monkeypatch,
        connection,
        finding={"id": 81, "season_id": 31, "kind": "heat"},
    )

    invalid = client.post("/api/v1/findings/81/review", json={"action": "correct"})
    assert invalid.status_code == 422

    response = client.post(
        "/api/v1/findings/81/review",
        json={"action": "correct", "new_cause": "pest_attack"},
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == "corrected"
    approval = next(
        params
        for query, params in connection.statements
        if "UPDATE seasons" in query
    )
    assert approval[0:2] == ("pest_attack", "corrected")
