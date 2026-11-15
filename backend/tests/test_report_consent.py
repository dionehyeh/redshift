import json
from contextlib import contextmanager
from itertools import combinations

import pytest

from app.services import report_service

CONSENT_FIELDS = ("field_profile", "history", "cards", "findings")
CONSENT_COMBINATIONS = tuple(
    combo
    for size in range(1, len(CONSENT_FIELDS) + 1)
    for combo in combinations(CONSENT_FIELDS, size)
)


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
        if "SELECT p.* FROM plans p" in query:
            return FakeCursor({"id": 41, "field_id": 12})
        if "SELECT id FROM users" in query:
            return FakeCursor({"id": 9})
        if "FROM fields WHERE id" in query:
            return FakeCursor(
                {
                    "elevation_m": 18,
                    "flood_prone": 0,
                    "drainage": "moderate",
                    "soil_ph": 5.7,
                }
            )
        if "FROM plan_cards" in query:
            return FakeCursor(
                rows=[
                    {
                        "position": 1,
                        "crop_id": 3,
                        "verdict": "Feasible",
                        "total": 82,
                        "factors_json": '{"water":80}',
                    }
                ]
            )
        if "FROM seasons s" in query:
            return FakeCursor(
                rows=[
                    {
                        "crop": "paddy",
                        "start_date": "2025-06-01",
                        "end_date": "2025-10-15",
                        "outcome": "good",
                        "loss_percent": 0,
                    }
                ]
            )
        if "FROM findings fi" in query:
            return FakeCursor(
                rows=[
                    {
                        "kind": "heat",
                        "week_from": 27,
                        "week_to": 29,
                        "deviation": 2.5,
                        "unit": "°C",
                        "crop_stage": "flowering",
                        "severity": "moderate",
                        "confidence": "high",
                        "source": "NASA POWER",
                        "resolution": "~50 km",
                        "text_plain": "Heat stress during flowering",
                        "explainer_key": "heat_stress",
                        "review_status": "confirmed",
                    }
                ]
            )
        if "INSERT INTO reports" in query:
            return FakeCursor({"id": 71})
        return FakeCursor()


@pytest.mark.parametrize("share_fields", CONSENT_COMBINATIONS)
def test_report_snapshot_contains_only_consenting_sections(monkeypatch, share_fields):
    connection = FakeConnection()

    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(report_service, "get_db", fake_get_db)
    result = report_service.create_report_service(
        farmer_id=7,
        plan_id=41,
        mentor_id=9,
        share_fields=list(share_fields),
        expires_days=14,
    )

    expected_keys = {
        "field_profile": "field",
        "history": "history",
        "cards": "cards",
        "findings": "findings",
    }
    expected_snapshot_keys = {expected_keys[field] for field in share_fields}
    assert set(result["snapshot"]) == expected_snapshot_keys
    assert set(json.loads(next(
        params[5]
        for query, params in connection.statements
        if "INSERT INTO reports" in query
    ))) == expected_snapshot_keys

    section_queries = {
        "field_profile": "FROM fields WHERE id",
        "history": "FROM seasons s",
        "cards": "FROM plan_cards",
        "findings": "FROM findings fi",
    }
    for consent, query_fragment in section_queries.items():
        assert any(
            query_fragment in query for query, _ in connection.statements
        ) is (consent in share_fields)


def test_history_and_findings_snapshots_omit_unconsented_private_details(monkeypatch):
    connection = FakeConnection()

    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(report_service, "get_db", fake_get_db)
    result = report_service.create_report_service(
        farmer_id=7,
        plan_id=41,
        mentor_id=9,
        share_fields=["history", "findings"],
        expires_days=14,
    )

    assert result["snapshot"]["history"] == [
        {
            "crop": "paddy",
            "start_date": "2025-06-01",
            "end_date": "2025-10-15",
            "outcome": "good",
            "loss_percent": 0,
        }
    ]
    assert result["snapshot"]["findings"] == [
        {
            "kind": "heat",
            "weeks": [27, 29],
            "deviation": 2.5,
            "unit": "°C",
            "crop_stage": "flowering",
            "severity": "moderate",
            "confidence": "high",
            "source": "NASA POWER",
            "resolution": "~50 km",
            "text": "Heat stress during flowering",
            "explainer_key": "heat_stress",
            "review_status": "confirmed",
        }
    ]
    assert "field_id" not in result["snapshot"]["findings"][0]
    assert "season_id" not in result["snapshot"]["findings"][0]


def test_invalid_or_empty_report_consent_is_rejected_before_database_access(
    monkeypatch,
):
    @contextmanager
    def unexpected_db_access():
        pytest.fail("database must not be accessed for invalid consent")
        yield

    monkeypatch.setattr(report_service, "get_db", unexpected_db_access)

    for share_fields in ([], ["findings", "unknown"]):
        with pytest.raises(report_service.AppError) as error:
            report_service.create_report_service(
                farmer_id=7,
                plan_id=41,
                mentor_id=9,
                share_fields=share_fields,
                expires_days=14,
            )
        assert error.value.code == "CONSENT_REQUIRED"
