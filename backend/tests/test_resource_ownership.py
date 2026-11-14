from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import deps
from app.errors import AppError, register_error_handlers
from app.routers import plans, reports, seasons
from app.services import report_service


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(
        self,
        *,
        plan=None,
        season=None,
        finding=None,
        finding_reports=None,
        report=None,
        report_owner=None,
    ):
        self.plan = plan
        self.season = season
        self.finding = finding
        self.finding_reports = finding_reports or []
        self.report = (
            {**report, "created_by": 7, "field_owner_id": 7}
            if report
            else None
        )
        self.report_owner = report_owner
        self.statements = []

    def execute(self, query, params=()):
        self.statements.append((query, params))
        if "FROM plans p" in query:
            return FakeCursor(self.plan)
        if "FROM seasons s" in query:
            return FakeCursor(self.season)
        if "FROM findings fi" in query:
            return FakeCursor(self.finding)
        if "SELECT r.*, f.farmer_id AS field_owner_id" in query:
            return FakeCursor(self.report)
        if "SELECT r.id, r.revoked_at" in query:
            return FakeCursor(self.report_owner)
        if "FROM reports r" in query:
            return FakeCursor(rows=self.finding_reports)
        if "SELECT r.id as report_id" in query:
            return FakeCursor(rows=[])
        if "INSERT INTO report_comments" in query:
            return FakeCursor({"id": 21})
        return FakeCursor()


def create_client(monkeypatch, user, connection):
    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(deps, "get_db", fake_get_db)
    for module in (plans, reports, seasons, report_service):
        monkeypatch.setattr(module, "get_db", fake_get_db, raising=False)

    app = FastAPI()
    register_error_handlers(app)
    app.include_router(plans.router, prefix="/api/v1")
    app.include_router(reports.router, prefix="/api/v1")
    app.include_router(seasons.router, prefix="/api/v1")
    app.dependency_overrides[deps.current_user] = lambda: dict(user)
    return TestClient(app)


FARMER = {"id": 7, "role": "farmer"}
MENTOR = {"id": 9, "role": "mentor"}


def test_plan_routes_hide_plans_not_owned_by_the_farmer(monkeypatch):
    client = create_client(monkeypatch, FARMER, FakeConnection(plan=None))

    responses = [
        client.get("/api/v1/plans/41"),
        client.post(
            "/api/v1/plans/41/rescore",
            json={"scenario": {"rain": 1.0, "temp": 0.0}},
        ),
        client.post("/api/v1/plans/41/choose", json={"card_id": 1}),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404]
    assert all(response.json()["error"]["code"] == "NOT_FOUND" for response in responses)


def test_season_routes_hide_seasons_not_owned_by_the_farmer(monkeypatch):
    client = create_client(monkeypatch, FARMER, FakeConnection(season=None))

    responses = [
        client.get("/api/v1/seasons/41"),
        client.patch("/api/v1/seasons/41", json={"outcome": "poor"}),
        client.post("/api/v1/seasons/41/analyze"),
        client.get("/api/v1/seasons/41/analysis"),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404, 404]
    assert all(response.json()["error"]["code"] == "NOT_FOUND" for response in responses)


def test_report_creation_rejects_another_farmers_plan(monkeypatch):
    connection = FakeConnection(plan=None)

    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(report_service, "get_db", fake_get_db)

    with pytest.raises(AppError) as error:
        report_service.create_report_service(7, 41, 9, ["cards"], 14)

    assert error.value.code == "NOT_FOUND"
    assert not any("INSERT INTO reports" in query for query, _ in connection.statements)


@pytest.mark.parametrize(
    "report",
    [
        {"shared_with": 8, "expires_at": "2999-01-01T00:00:00", "status": "sent"},
        {"shared_with": 9, "expires_at": "2000-01-01T00:00:00", "status": "sent"},
        {
            "shared_with": 9,
            "expires_at": "2999-01-01T00:00:00",
            "status": "revoked",
            "revoked_at": "2026-01-01T00:00:00",
        },
    ],
)
def test_comments_require_the_active_report_recipient(monkeypatch, report):
    connection = FakeConnection(report=report)
    client = create_client(monkeypatch, MENTOR, connection)

    response = client.post("/api/v1/reports/41/comments", json={"text": "Useful note"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] in {"FORBIDDEN", "REPORT_UNAVAILABLE"}
    assert not any("INSERT INTO report_comments" in query for query, _ in connection.statements)


def test_active_report_recipient_can_comment(monkeypatch):
    connection = FakeConnection(
        report={
            "shared_with": 9,
            "expires_at": "2999-01-01T00:00:00",
            "status": "sent",
        }
    )
    client = create_client(monkeypatch, MENTOR, connection)

    response = client.post("/api/v1/reports/41/comments", json={"text": "Useful note"})

    assert response.status_code == 201
    assert any("INSERT INTO report_comments" in query for query, _ in connection.statements)


@pytest.mark.parametrize(
    ("report", "expected_code"),
    [
        (
            {
                "shared_with": 8,
                "expires_at": "2999-01-01T00:00:00",
                "status": "sent",
            },
            "FORBIDDEN",
        ),
        (
            {
                "shared_with": 9,
                "expires_at": "2000-01-01T00:00:00",
                "status": "sent",
            },
            "REPORT_UNAVAILABLE",
        ),
    ],
)
def test_report_reads_require_recipient_and_active_consent(monkeypatch, report, expected_code):
    client = create_client(monkeypatch, MENTOR, FakeConnection(report=report))

    response = client.get("/api/v1/reports/41")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == expected_code


def test_mentor_inbox_query_excludes_revoked_and_expired_reports(monkeypatch):
    connection = FakeConnection()
    client = create_client(monkeypatch, MENTOR, connection)

    response = client.get("/api/v1/mentor/inbox")

    assert response.status_code == 200
    inbox_query, params = next(
        (query, params)
        for query, params in connection.statements
        if "SELECT r.id as report_id" in query
    )
    assert "r.status <> 'revoked'" in inbox_query
    assert "r.revoked_at IS NULL" in inbox_query
    assert "r.expires_at > ?" in inbox_query
    assert params[0] == MENTOR["id"]


def test_farmer_cannot_revoke_another_farmers_report(monkeypatch):
    connection = FakeConnection(report_owner=None)
    client = create_client(monkeypatch, FARMER, connection)

    response = client.post("/api/v1/reports/41/revoke")

    assert response.status_code == 404
    assert not any("UPDATE reports" in query for query, _ in connection.statements)
    assert not any("INSERT INTO audit_log" in query for query, _ in connection.statements)


def test_farmer_can_revoke_owned_report(monkeypatch):
    connection = FakeConnection(report_owner={"id": 41, "revoked_at": None})
    client = create_client(monkeypatch, FARMER, connection)

    response = client.post("/api/v1/reports/41/revoke")

    assert response.status_code == 200
    assert response.json() == {"status": "revoked"}
    assert any("UPDATE reports SET status = 'revoked'" in query for query, _ in connection.statements)


def test_mentor_can_review_findings_only_from_an_active_findings_share(monkeypatch):
    connection = FakeConnection(
        finding={"id": 13, "field_id": 41, "farmer_id": 7, "season_id": 15, "kind": "heat"},
        finding_reports=[
            {
                "fields_shared": '["field_profile", "findings"]',
                "expires_at": "2999-01-01T00:00:00",
                "status": "sent",
            }
        ],
    )
    client = create_client(monkeypatch, MENTOR, connection)

    response = client.post(
        "/api/v1/findings/13/review",
        json={"action": "confirm", "new_cause": "heat_stress"},
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == "confirmed"


def test_mentor_cannot_review_a_finding_without_consent(monkeypatch):
    connection = FakeConnection(
        finding={"id": 13, "field_id": 41, "farmer_id": 7, "season_id": 15, "kind": "heat"},
        finding_reports=[
            {
                "fields_shared": '["field_profile"]',
                "expires_at": "2999-01-01T00:00:00",
                "status": "sent",
            }
        ],
    )
    client = create_client(monkeypatch, MENTOR, connection)

    response = client.post(
        "/api/v1/findings/13/review",
        json={"action": "confirm", "new_cause": "heat_stress"},
    )

    assert response.status_code == 404
    assert not any("UPDATE findings" in query for query, _ in connection.statements)
