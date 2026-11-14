import json
from contextlib import contextmanager
from datetime import date

from app.routers import plans as plans_router
from app.services import plan_service

SEASONS = [
    {"key": "puncha", "start_week": 2},
    {"key": "virippu", "start_week": 18},
    {"key": "mundakan", "start_week": 38},
]


class FakeCursor:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, *, plan=None, field=None, cards=None, history=None):
        self.plan = plan
        self.field = field
        self.cards = cards or []
        self.history = history or []
        self.statements = []

    def execute(self, query, params=()):
        self.statements.append((query, params))
        if "FROM seasons s" in query:
            return FakeCursor(rows=self.history)
        if "INSERT INTO plans" in query:
            return FakeCursor({"id": 13})
        if "FROM plans WHERE id" in query:
            return FakeCursor(self.plan)
        if "FROM fields WHERE id" in query:
            return FakeCursor(self.field)
        if "FROM plan_cards pc" in query:
            return FakeCursor(rows=self.cards)
        return FakeCursor()


def use_connection(monkeypatch, module, connection):
    @contextmanager
    def fake_get_db():
        yield connection

    monkeypatch.setattr(module, "get_db", fake_get_db)


def test_plan_timing_uses_configured_seasons_and_allows_next_week_override(monkeypatch):
    monkeypatch.setattr(plan_service, "get_seasons_list", lambda: SEASONS)

    assert plan_service._resolve_plan_timing({"season": "puncha"}) == (
        "puncha",
        2,
        18,
    )
    assert plan_service._resolve_plan_timing(
        {"season": "puncha", "start_week": 4, "next_week": 52}
    ) == ("puncha", 4, 52)


def test_history_snapshot_uses_only_approved_crop_failure_causes():
    history = plan_service._history_entry(
        {
            "crop": "paddy",
            "family": "grass",
            "n_effect": "heavy",
            "outcome": "failed",
            "approval_status": "approved",
            "approved_cause": "water_shortage",
            "suspected_cause": "pests",
        }
    )

    assert history == {
        "crop": "paddy",
        "family": "grass",
        "n_effect": "heavy",
        "outcome": "failed",
        "cause_approved": True,
        "cause": "water_stress",
    }


def test_upcoming_week_start_handles_iso_year_boundaries():
    assert plan_service.upcoming_week_start(2, date(2025, 12, 29)) == date(
        2026, 1, 5
    )
    assert plan_service.upcoming_week_start(1, date(2026, 3, 1)) == date(
        2027, 1, 4
    )


def test_create_plan_persists_resolved_timing_and_rotation_history(monkeypatch):
    history_row = {
        "crop": "paddy",
        "family": "grass",
        "n_effect": "heavy",
        "outcome": "failed",
        "approval_status": "approved",
        "approved_cause": "pests",
    }
    connection = FakeConnection(
        field={"id": 3},
        history=[history_row],
    )
    use_connection(monkeypatch, plan_service, connection)
    monkeypatch.setattr(plan_service, "get_seasons_list", lambda: SEASONS)
    monkeypatch.setattr(
        plan_service,
        "build_scoring_environment",
        lambda **kwargs: {
            "scenario": kwargs["scenario"],
            "outlook_info": {"factor": 0.9},
            "weights": {"water": 30},
            "stored_mm": 75,
            "stored_basis": "farmer answer",
        },
    )
    monkeypatch.setattr(
        plan_service, "load_crops", lambda: [{"name": "paddy"}]
    )
    monkeypatch.setattr(
        plan_service,
        "pick_three",
        lambda *_args: [
            {
                "crop": "paddy",
                "total": 75,
                "factors": {},
                "colors": {},
                "worst": 60,
                "holds_up_best": True,
            }
        ],
    )
    monkeypatch.setattr(plan_service, "verdict", lambda _evaluation: "Feasible")
    monkeypatch.setattr(
        plan_service,
        "get_template_narrative",
        lambda *_args: {
            "why": "",
            "risks": "",
            "previous_crop_effect": "",
            "next_step": "",
            "watch_for": "",
            "after_this": "",
        },
    )

    result = plan_service.create_plan_service(
        3,
        {
            "mode": "suggest",
            "season": "puncha",
            "stored_water_answer": "moist",
            "scenario": {"rain": 1.0, "temp": 0.0},
        },
    )

    plan_insert = next(
        params for query, params in connection.statements if "INSERT INTO plans" in query
    )
    persisted_inputs = json.loads(plan_insert[-1])
    assert result["plan_id"] == 13
    assert (persisted_inputs["start_week"], persisted_inputs["next_week"]) == (2, 18)
    assert persisted_inputs["history"][0]["cause"] == "pest"
    assert persisted_inputs["stored_water_answer"] == "moist"
    card_insert = next(
        params
        for query, params in connection.statements
        if "INSERT INTO plan_cards" in query
    )
    assert json.loads(card_insert[-2]) == {
        "worst_case_total": 60,
        "holds_up_best": True,
    }


def test_rescore_reuses_saved_inputs_and_persists_updated_card_data(monkeypatch):
    history = [{"crop": "rice", "family": "grass", "n_effect": "heavy"}]
    saved_inputs = {
        "next_week": 18,
        "stored_water_answer": "dry",
        "history": history,
        "farmer_crop": None,
    }
    connection = FakeConnection(
        plan={
            "id": 5,
            "field_id": 3,
            "start_week": 2,
            "toggle": "play_safe",
            "inputs_json": json.dumps(saved_inputs),
        },
        field={"id": 3},
        cards=[
            {
                "id": 11,
                "position": 1,
                "crop_id": 8,
                "crop_name": "paddy",
                "is_existing_rotation": 1,
                "factors_json": json.dumps({"water": 60}),
            }
        ],
    )
    use_connection(monkeypatch, plan_service, connection)
    calls = {}

    def fake_environment(**kwargs):
        calls.update(kwargs)
        return {
            "scenario": kwargs["scenario"],
            "outlook_info": {"factor": 0.9},
            "weights": {"water": 30},
            "stored_mm": 0.0,
            "stored_basis": "farmer answer",
        }

    monkeypatch.setattr(plan_service, "build_scoring_environment", fake_environment)
    monkeypatch.setattr(
        plan_service,
        "load_crops",
        lambda: [{"name": "paddy", "family": "grass"}],
    )
    monkeypatch.setattr(plan_service, "verdict", lambda _evaluation: "Feasible")
    monkeypatch.setattr(
        plan_service,
        "get_template_narrative",
        lambda *_args: {
            "why": "",
            "risks": "",
            "previous_crop_effect": "",
            "next_step": "",
            "watch_for": "",
            "after_this": "",
        },
    )

    def fake_evaluate(crop, _env, stress=None):
        return {
            "crop": crop["name"],
            "total": 80 if stress is None else 55,
            "factors": {"water": 80, "rotation": 80, "soil": 80},
            "colors": {},
            "red": [],
        }

    monkeypatch.setattr(plan_service, "evaluate", fake_evaluate)

    result = plan_service.rescore_plan_service(
        5, {"rain": 1.2, "temp": 2.0}, new_toggle="earn_more"
    )

    assert calls["history"] == history
    assert calls["stored_water_answer"] == "dry"
    assert calls["next_week"] == 18
    assert result["cards"][0]["robustness"] == {
        "worst_case_total": 55,
        "holds_up_best": False,
    }
    card_update = next(
        params
        for query, params in connection.statements
        if "UPDATE plan_cards" in query
    )
    assert json.loads(card_update[7])["worst_case_total"] == 55
    plan_update = next(
        params for query, params in connection.statements if "UPDATE plans" in query
    )
    assert plan_update[0] == "earn_more"
    assert json.loads(plan_update[1]) == {"rain": 1.2, "temp": 2.0}
    assert json.loads(plan_update[4])["stored_water_answer"] == "dry"


def test_get_plan_returns_persisted_card_crop_and_robustness(monkeypatch):
    saved_inputs = {"farmer_choice_card": {"crop": "maize", "total": 72}}
    connection = FakeConnection(
        cards=[
            {
                "position": 1,
                "is_existing_rotation": 1,
                "crop_name": "paddy",
                "crop_id": 8,
                "verdict": "Feasible",
                "total": 78,
                "factors_json": "{}",
                "flags_json": "{}",
                "confidence_json": '{"level":"medium","reason":"model"}',
                "robustness_json": '{"worst_case_total":61,"holds_up_best":true}',
                "text_json": "{}",
                "notes_json": '["saved note"]',
                "evidence_json": (
                    '{"needs_local_review":["seed availability"],'
                    '"explainer_keys":["rotation"]}'
                ),
            }
        ]
    )
    use_connection(monkeypatch, plans_router, connection)

    result = plans_router.get_plan(
        5,
        user={"id": 7},
        plan={
            "chosen_card_id": 1,
            "outlook_json": "{}",
            "weights_json": "{}",
            "inputs_json": json.dumps(saved_inputs),
        },
    )

    assert result["cards"][0]["crop"] == "paddy"
    assert result["cards"][0]["robustness"]["worst_case_total"] == 61
    assert result["cards"][0]["notes"] == ["saved note"]
    assert result["farmer_choice_card"] == saved_inputs["farmer_choice_card"]
