import json
from datetime import date

from app.db import get_db
from app.engine.scoring import (
    FACTOR_TO_MESSAGE,
    STRESS,
    evaluate,
    load_crops,
    pick_three,
    verdict,
)
from app.errors import AppError
from app.services.reference_service import get_seasons_list
from app.services.scoring_service import build_scoring_environment
from app.services.text_service import get_template_narrative


def _season_schedule() -> list[dict]:
    seasons = get_seasons_list()
    if not isinstance(seasons, list):
        raise AppError(
            "SEASON_DATA_UNAVAILABLE",
            "Planting season schedule is invalid",
            status=503,
        )
    valid_seasons = []
    for season in seasons:
        if not isinstance(season, dict):
            raise AppError(
                "SEASON_DATA_UNAVAILABLE",
                "Planting season schedule is invalid",
                status=503,
            )
        key = season.get("key")
        start_week = season.get("start_week")
        if (
            key not in {"virippu", "mundakan", "puncha"}
            or type(start_week) is not int
            or not 1 <= start_week <= 52
        ):
            raise AppError(
                "SEASON_DATA_UNAVAILABLE",
                "Planting season schedule is invalid",
                status=503,
            )
        valid_seasons.append({"key": key, "start_week": start_week})
    if (
        {season["key"] for season in valid_seasons}
        != {"virippu", "mundakan", "puncha"}
        or len({season["start_week"] for season in valid_seasons})
        != len(valid_seasons)
    ):
        raise AppError(
            "SEASON_DATA_UNAVAILABLE",
            "Planting season schedule is unavailable",
            status=503,
        )
    return sorted(valid_seasons, key=lambda season: season["start_week"])


def _history_entry(row: dict) -> dict:
    cause = row.get("approved_cause")
    if cause == "pests":
        cause = "pest"
    elif cause == "water_shortage":
        cause = "water_stress"
    approved = row.get("approval_status") in {"approved", "corrected"}
    return {
        "crop": row.get("crop"),
        "family": row.get("family"),
        "n_effect": row.get("n_effect"),
        "outcome": row.get("outcome"),
        "cause_approved": approved,
        "cause": cause if approved else None,
    }


def _resolve_plan_timing(request_body: dict) -> tuple[str, int, int]:
    seasons = _season_schedule()
    requested_season = request_body.get("season")
    season = next(
        (item for item in seasons if item["key"] == requested_season),
        None,
    )
    if requested_season and season is None:
        raise AppError(
            "INVALID_SEASON",
            "The requested planting season is not configured",
            status=422,
        )

    start_week = request_body.get("start_week")
    if start_week is None:
        if season is None:
            current_week = date.today().isocalendar().week
            season = next(
                (item for item in seasons if item["start_week"] > current_week),
                seasons[0],
            )
        start_week = season["start_week"]
    else:
        if season is None:
            eligible = [
                item for item in seasons if item["start_week"] <= start_week
            ]
            season = eligible[-1] if eligible else seasons[-1]

    next_week = request_body.get("next_week")
    if next_week is None:
        season_index = seasons.index(season)
        next_week = seasons[(season_index + 1) % len(seasons)]["start_week"]
    if next_week == start_week:
        raise AppError(
            "INVALID_PLAN_TIMING",
            "The following season must differ from the plan start week",
            status=422,
        )
    return season["key"], start_week, next_week


def upcoming_week_start(week: int, today: date | None = None) -> date:
    if not 1 <= week <= 52:
        raise ValueError("week must be between 1 and 52")
    today = today or date.today()
    iso_year = today.isocalendar().year
    week_start = date.fromisocalendar(iso_year, week, 1)
    if week_start < today:
        week_start = date.fromisocalendar(iso_year + 1, week, 1)
    return week_start


def _add_robustness(crop: dict, env: dict) -> dict:
    evaluation = evaluate(crop, env)
    evaluation["worst"] = min(
        evaluate(crop, env, stress)["total"] for stress in STRESS
    )
    return evaluation


def _set_robustness_leaders(evaluations: list[dict]) -> None:
    if not evaluations:
        return
    best_worst = max(item["worst"] for item in evaluations)
    minimum_worst = min(item["worst"] for item in evaluations)
    leader = next(
        (
            index
            for index, item in enumerate(evaluations)
            if item["worst"] == best_worst and not item.get("red")
        ),
        None,
    )
    for index, item in enumerate(evaluations):
        item["holds_up_best"] = bool(
            leader == index
            and len(evaluations) > 1
            and best_worst - minimum_worst >= 5
        )


def create_plan_service(field_id: int, request_body: dict) -> dict:
    season, start_week, next_week = _resolve_plan_timing(request_body)
    with get_db() as conn:
        field_row = conn.execute(
            "SELECT * FROM fields WHERE id = ?", (field_id,)
        ).fetchone()
        if not field_row:
            raise AppError("NOT_FOUND", "Field not found", status=404)
        field = dict(field_row)
        hist_rows = conn.execute(
            """SELECT s.*, c.name AS crop, c.family, c.n_effect
               FROM seasons s
               LEFT JOIN crops c ON s.crop_id = c.id
               WHERE s.field_id = ? AND s.status = 'completed'
               ORDER BY s.end_date DESC LIMIT 3""",
            (field_id,),
        ).fetchall()
        history = [_history_entry(dict(row)) for row in hist_rows]

    crops = load_crops()
    customary_crop = history[0].get("crop") if history else None
    customary_crop = customary_crop or "paddy"
    stored_water_answer = request_body.get("stored_water_answer")
    toggle = request_body.get("toggle")
    scenario = request_body.get("scenario")
    env = build_scoring_environment(
        field=field,
        history=history,
        start_week=start_week,
        next_week=next_week,
        stored_water_answer=stored_water_answer,
        toggle=toggle,
        scenario=scenario,
    )

    mode = request_body.get("mode", "suggest")
    farmer_crop_name = request_body.get("crop")
    farmer_choice_card = None
    crops_by_name = {crop["name"]: crop for crop in crops}
    if mode == "farmer_led" and farmer_crop_name:
        crop = crops_by_name.get(farmer_crop_name)
        if crop:
            evaluation = _add_robustness(crop, env)
            evaluation["verdict"] = verdict(evaluation)
            farmer_choice_card = _format_card_dict(
                evaluation, 1, is_customary=False
            )
        else:
            farmer_choice_card = {
                "id": 999,
                "position": 1,
                "is_existing_rotation": False,
                "crop": farmer_crop_name,
                "verdict": "Not assessed",
                "total": None,
                "factors": {},
                "colors": {},
                "confidence": {
                    "level": "low",
                    "reason": "Crop data not in regional catalog",
                },
                "robustness": {
                    "worst_case_total": None,
                    "holds_up_best": False,
                },
                "text": {
                    "why": "We do not have regional agronomic baselines for this cultivar yet.",
                    "risks": "Verify local suitability with an agricultural extension officer.",
                    "previous_crop_effect": "",
                    "next_step": "Tap 'Get Help' to consult a mentor.",
                    "watch_for": "",
                    "after_this": "",
                },
                "notes": ["Uncataloged crop"],
                "needs_local_review": [
                    "variety traits",
                    "local pest resistance",
                    "irrigation requirement",
                ],
                "explainer_keys": [],
            }

    raw_cards = pick_three(crops, env, customary_crop)
    formatted_cards = []
    for index, card in enumerate(raw_cards):
        card["verdict"] = verdict(card)
        formatted_cards.append(
            _format_card_dict(
                card,
                index + 1,
                is_customary=(index == 0),
            )
        )

    inputs = {
        "season": season,
        "start_week": start_week,
        "next_week": next_week,
        "stored_water_answer": stored_water_answer,
        "stored_mm": env["stored_mm"],
        "stored_basis": env["stored_basis"],
        "stored_water": env["stored_water"],
        "source_gaps": env["source_gaps"],
        "scenario": env["scenario"],
        "toggle": toggle,
        "history": history,
        "farmer_crop": farmer_crop_name,
        "farmer_reason": request_body.get("reason"),
        "farmer_choice_card": farmer_choice_card,
    }

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO plans
               (field_id, mode, start_week, toggle, farmer_crop_id, farmer_reason,
                scenario_json, outlook_json, weights_json, inputs_json)
               VALUES (?, ?, ?, ?, (SELECT id FROM crops WHERE name = ?), ?, ?, ?, ?, ?)
               RETURNING id""",
            (
                field_id,
                mode,
                start_week,
                toggle,
                farmer_crop_name,
                request_body.get("reason"),
                json.dumps(env["scenario"]),
                json.dumps(env["outlook_info"]),
                json.dumps(env["weights"]),
                json.dumps(inputs),
            ),
        )
        plan_id = cursor.fetchone()["id"]

        for card in formatted_cards:
            evidence = {
                "needs_local_review": card["needs_local_review"],
                "explainer_keys": card["explainer_keys"],
            }
            conn.execute(
                """INSERT INTO plan_cards
                   (plan_id, position, is_existing_rotation, crop_id, verdict, total,
                    factors_json, flags_json, confidence_json, evidence_json,
                    notes_json, robustness_json, text_json)
                   VALUES (?, ?, ?, (SELECT id FROM crops WHERE name = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    plan_id,
                    card["position"],
                    1 if card["is_existing_rotation"] else 0,
                    card["crop"],
                    card["verdict"],
                    card["total"],
                    json.dumps(card["factors"]),
                    json.dumps(card["colors"]),
                    json.dumps(card["confidence"]),
                    json.dumps(evidence),
                    json.dumps(card["notes"]),
                    json.dumps(card["robustness"]),
                    json.dumps(card["text"]),
                ),
            )

    return {
        "plan_id": plan_id,
        "outlook": env["outlook_info"],
        "weights": env["weights"],
        "inputs": inputs,
        "cards": formatted_cards,
        "farmer_choice_card": farmer_choice_card,
        "chosen_card_id": None,
    }


def rescore_plan_service(
    plan_id: int, new_scenario: dict, new_toggle: str | None = None
) -> dict:
    with get_db() as conn:
        plan_row = conn.execute(
            "SELECT * FROM plans WHERE id = ?", (plan_id,)
        ).fetchone()
        if not plan_row:
            raise AppError("NOT_FOUND", "Plan not found", status=404)
        plan = dict(plan_row)
        field_row = conn.execute(
            "SELECT * FROM fields WHERE id = ?", (plan["field_id"],)
        ).fetchone()
        if not field_row:
            raise AppError("NOT_FOUND", "Plan field not found", status=404)
        field = dict(field_row)
        card_rows = conn.execute(
            """SELECT pc.*, c.name AS crop_name
               FROM plan_cards pc
               LEFT JOIN crops c ON pc.crop_id = c.id
               WHERE pc.plan_id = ? ORDER BY pc.position ASC""",
            (plan_id,),
        ).fetchall()

    inputs = json.loads(plan["inputs_json"]) if plan["inputs_json"] else {}
    if "next_week" not in inputs:
        _, _, inputs["next_week"] = _resolve_plan_timing(
            {"start_week": plan["start_week"], "season": inputs.get("season")}
        )
    history = inputs.get("history", [])
    toggle = new_toggle if new_toggle is not None else plan["toggle"]
    env = build_scoring_environment(
        field=field,
        history=history,
        start_week=plan["start_week"],
        next_week=inputs["next_week"],
        stored_water_answer=inputs.get("stored_water_answer"),
        toggle=toggle,
        scenario=new_scenario,
    )

    crops_by_name = {crop["name"]: crop for crop in load_crops()}
    evaluated_cards = []
    for row in card_rows:
        crop_name = row["crop_name"]
        crop = crops_by_name.get(crop_name)
        if crop is None:
            raise AppError(
                "PLAN_CARD_CROP_UNAVAILABLE",
                "A crop in this plan is no longer available for scoring",
                status=409,
                details={"plan_id": plan_id, "card_id": row["position"]},
            )
        evaluation = _add_robustness(crop, env)
        evaluation["verdict"] = verdict(evaluation)
        evaluated_cards.append((row, crop_name, evaluation))
    _set_robustness_leaders([item[2] for item in evaluated_cards])

    rescored_cards = []
    changes = []
    persisted_cards = []
    for row, crop_name, evaluation in evaluated_cards:
        formatted = _format_card_dict(
            evaluation,
            row["position"],
            is_customary=bool(row["is_existing_rotation"]),
        )
        rescored_cards.append(formatted)
        old_factors = json.loads(row["factors_json"])
        for factor, old_value in old_factors.items():
            new_value = formatted["factors"].get(factor, old_value)
            if abs(new_value - old_value) >= 10:
                changes.append(
                    {
                        "crop": crop_name,
                        "factor": factor,
                        "from": old_value,
                        "to": new_value,
                        "message_key": FACTOR_TO_MESSAGE.get(
                            factor, "arrange_irrigation"
                        ),
                    }
                )
        evidence = {
            "needs_local_review": formatted["needs_local_review"],
            "explainer_keys": formatted["explainer_keys"],
        }
        persisted_cards.append(
            (
                formatted,
                row["id"],
                json.dumps(evidence),
            )
        )

    farmer_choice_card = None
    farmer_crop_name = inputs.get("farmer_crop")
    farmer_crop = crops_by_name.get(farmer_crop_name)
    if farmer_crop is not None:
        evaluation = _add_robustness(farmer_crop, env)
        evaluation["verdict"] = verdict(evaluation)
        farmer_choice_card = _format_card_dict(
            evaluation, 1, is_customary=False
        )
    elif farmer_crop_name:
        farmer_choice_card = inputs.get("farmer_choice_card")
    inputs.update(
        {
            "scenario": new_scenario,
            "toggle": toggle,
            "stored_mm": env["stored_mm"],
            "stored_basis": env["stored_basis"],
            "stored_water": env["stored_water"],
            "source_gaps": env["source_gaps"],
            "farmer_choice_card": farmer_choice_card,
        }
    )

    with get_db() as conn:
        for formatted, card_id, evidence_json in persisted_cards:
            conn.execute(
                """UPDATE plan_cards
                   SET verdict = ?, total = ?, factors_json = ?, flags_json = ?,
                       confidence_json = ?, evidence_json = ?, notes_json = ?,
                       robustness_json = ?, text_json = ?
                   WHERE id = ?""",
                (
                    formatted["verdict"],
                    formatted["total"],
                    json.dumps(formatted["factors"]),
                    json.dumps(formatted["colors"]),
                    json.dumps(formatted["confidence"]),
                    evidence_json,
                    json.dumps(formatted["notes"]),
                    json.dumps(formatted["robustness"]),
                    json.dumps(formatted["text"]),
                    card_id,
                ),
            )
        conn.execute(
            """UPDATE plans
               SET toggle = ?, scenario_json = ?, outlook_json = ?,
                   weights_json = ?, inputs_json = ?
               WHERE id = ?""",
            (
                toggle,
                json.dumps(new_scenario),
                json.dumps(env["outlook_info"]),
                json.dumps(env["weights"]),
                json.dumps(inputs),
                plan_id,
            ),
        )

    return {
        "cards": rescored_cards,
        "changes": changes,
        "farmer_choice_card": farmer_choice_card,
    }


def _format_card_dict(ev: dict, position: int, is_customary: bool) -> dict:
    narrative = get_template_narrative(
        ev["crop"], ev.get("verdict", "Feasible"), ev["factors"]
    )
    notes = []
    if ev["factors"].get("water", 100) < 40:
        notes.append(
            "Severe water deficit expected during key vegetative window"
        )
    if ev["factors"].get("rotation", 100) < 40:
        notes.append(
            "Expect higher fertilizer and pest-control cost from family repetition"
        )

    needs_review = ["seed variety availability", "current mandi price"]
    if ev["factors"].get("water", 100) < 65:
        needs_review.append("supplemental irrigation availability")
    if ev["factors"].get("soil", 100) < 65:
        needs_review.append("liming recommendations for acidic soil")

    return {
        "id": position,
        "position": position,
        "is_existing_rotation": is_customary,
        "crop": ev["crop"],
        "verdict": ev.get("verdict", "Feasible"),
        "total": ev["total"],
        "factors": ev["factors"],
        "colors": ev["colors"],
        "confidence": {
            "level": "medium",
            "reason": "Satellite precipitation and soil model estimate",
        },
        "robustness": {
            "worst_case_total": ev.get("worst"),
            "holds_up_best": ev.get("holds_up_best", False),
        },
        "text": narrative,
        "notes": notes,
        "needs_local_review": needs_review,
        "explainer_keys": ["water_balance", "rotation", "confidence"],
    }
