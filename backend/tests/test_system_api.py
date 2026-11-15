from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import deps, jobs
from app.errors import register_error_handlers
from app.routers import system


class FakeCursor:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row=None):
        self.row = row
        self.query = None
        self.params = None

    def execute(self, query, params=()):
        self.query = query
        self.params = params
        return FakeCursor(self.row)


FARMER = {"id": 7, "role": "farmer"}


def create_client(monkeypatch, user, connection):
    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(jobs, "get_db", fake_get_db)
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(system.router, prefix="/api/v1")
    app.dependency_overrides[deps.current_user] = lambda: dict(user)
    return TestClient(app)


def test_job_status_requires_authentication_and_farmer_role(monkeypatch):
    connection = FakeConnection()
    client = create_client(monkeypatch, {"id": 9, "role": "mentor"}, connection)

    response = client.get("/api/v1/jobs/job-1")

    assert response.status_code == 403
    assert connection.query is None


def test_job_status_only_returns_jobs_for_owned_field_or_season(monkeypatch):
    connection = FakeConnection(
        row={
            "id": "job-1",
            "kind": "season_analysis",
            "target_id": 31,
            "status": "done_with_gaps",
            "step": "done",
            "progress": 100,
            "steps_json": '["loading_season"]',
            "result_json": '{"findings_count":1}',
            "error": None,
        }
    )
    client = create_client(monkeypatch, FARMER, connection)

    response = client.get("/api/v1/jobs/job-1")

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-1",
        "status": "done_with_gaps",
        "step": "done",
        "progress": 100,
        "steps": ["loading_season"],
        "error": None,
        "result": {"findings_count": 1},
    }
    assert "onboarding_field.farmer_id = ?" in connection.query
    assert "analysis_field.farmer_id = ?" in connection.query
    assert connection.params == ("job-1", FARMER["id"], FARMER["id"])


def test_job_status_hides_jobs_not_owned_by_the_farmer(monkeypatch):
    connection = FakeConnection()
    client = create_client(monkeypatch, FARMER, connection)

    response = client.get("/api/v1/jobs/job-owned-by-someone-else")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"
