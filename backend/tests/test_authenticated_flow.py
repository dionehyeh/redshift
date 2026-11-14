from contextlib import contextmanager

from fastapi.testclient import TestClient

from app import deps, main
from app.routers import reports
from app.services import report_service


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class ReportFlowConnection:
    def __init__(self):
        self.report = None
        self.comments = []

    def execute(self, query, params=()):
        if "SELECT p.* FROM plans p" in query:
            return FakeCursor({"id": 41, "field_id": 12})
        if "SELECT id FROM users WHERE id" in query:
            return FakeCursor({"id": 9})
        if "FROM plan_cards" in query:
            return FakeCursor(
                rows=[
                    {
                        "position": 1,
                        "crop_id": 2,
                        "verdict": "Feasible",
                        "total": 82,
                        "factors_json": '{"water":80}',
                    }
                ]
            )
        if "INSERT INTO reports" in query:
            self.report = {
                "id": 71,
                "created_by": params[1],
                "share_token": params[2],
                "shared_with": params[3],
                "fields_shared": params[4],
                "snapshot_json": params[5],
                "expires_at": params[6],
                "revoked_at": None,
                "status": "sent",
                "created_at": "2026-11-15T00:00:00",
                "field_owner_id": params[1],
            }
            return FakeCursor({"id": 71})
        if "SELECT r.*, f.farmer_id AS field_owner_id" in query:
            if self.report is None:
                return FakeCursor()
            return FakeCursor({**self.report, "field_owner_id": 7})
        if "SELECT * FROM report_comments" in query:
            return FakeCursor(rows=list(self.comments))
        if "INSERT INTO report_comments" in query:
            comment = {
                "id": len(self.comments) + 1,
                "author_id": params[1],
                "author_label": params[2],
                "body": params[3],
                "created_at": "2026-11-15T00:01:00",
            }
            self.comments.append(comment)
            return FakeCursor({"id": comment["id"]})
        if "UPDATE reports SET status = 'viewed'" in query:
            if self.report["status"] == "sent":
                self.report["status"] = "viewed"
        elif "UPDATE reports SET status = 'commented'" in query:
            self.report["status"] = "commented"
        elif "UPDATE reports SET status = 'revoked'" in query:
            self.report["status"] = "revoked"
            self.report["revoked_at"] = params[0]
        elif "SELECT r.id, r.revoked_at" in query:
            if self.report and self.report["created_by"] == params[1]:
                return FakeCursor(
                    {"id": self.report["id"], "revoked_at": self.report["revoked_at"]}
                )
            return FakeCursor()
        return FakeCursor()


def test_authenticated_report_consultation_lifecycle(monkeypatch):
    connection = ReportFlowConnection()
    user = {"id": 7, "role": "farmer"}

    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(report_service, "get_db", fake_get_db)
    monkeypatch.setattr(reports, "get_db", fake_get_db)
    monkeypatch.setitem(main.app.dependency_overrides, deps.current_user, lambda: dict(user))

    with TestClient(main.app) as client:
        created = client.post(
            "/api/v1/reports",
            json={
                "plan_id": 41,
                "mentor_id": 9,
                "share": ["cards"],
                "expires_days": 14,
            },
        )
        assert created.status_code == 201
        report_id = created.json()["id"]

        user.update(id=9, role="mentor")
        mentor_view = client.get(f"/api/v1/reports/{report_id}")
        assert mentor_view.status_code == 200
        assert mentor_view.json()["snapshot"] == {
            "cards": [
                {
                    "position": 1,
                    "crop_id": 2,
                    "verdict": "Feasible",
                    "total": 82,
                    "factors": {"water": 80},
                }
            ]
        }
        assert mentor_view.json()["shared_fields"] == ["cards"]

        comment = client.post(
            f"/api/v1/reports/{report_id}/comments",
            json={"text": "Consider an earlier planting date."},
        )
        assert comment.status_code == 201

        user.update(id=7, role="farmer")
        farmer_view = client.get(f"/api/v1/reports/{report_id}")
        assert farmer_view.status_code == 200
        assert farmer_view.json()["status"] == "commented"
        assert farmer_view.json()["comments"][0]["body"] == (
            "Consider an earlier planting date."
        )

        revoked = client.post(f"/api/v1/reports/{report_id}/revoke")
        assert revoked.status_code == 200
        assert revoked.json()["status"] == "revoked"

        user.update(id=9, role="mentor")
        denied = client.get(f"/api/v1/reports/{report_id}")
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "REPORT_UNAVAILABLE"
