import json
from app.db import get_db
from app.engine.scoring import load_crops, evaluate, verdict, pick_three, FACTOR_TO_MESSAGE
from app.services.scoring_service import build_scoring_environment
from app.services.text_service import get_template_narrative

def create_plan_service(field_id: int, request_body: dict) -> dict:
    with get_db() as conn:
        field = dict(conn.execute("SELECT * FROM fields WHERE id = ?", (field_id,)).fetchone())
        hist_rows = conn.execute(
            """SELECT s.*, c.family, c.n_effect 
               FROM seasons s 
               LEFT JOIN crops c ON s.crop_id = c.id 
               WHERE s.field_id = ? AND s.status = 'completed'
               ORDER BY s.end_date DESC LIMIT 3""",
            (field_id,),
        ).fetchall()
        history = [dict(r) for r in hist_rows]

    start_week = request_body.get("start_week") or 2
    next_week = 20
    crops = load_crops()
    customary_crop = history[0]["crop_id"] if history else "paddy"
    if isinstance(customary_crop, int):
        customary_crop = "paddy"

    env = build_scoring_environment(
        field=field,
        history=history,
        start_week=start_week,
        next_week=next_week,
        stored_water_answer=request_body.get("stored_water_answer"),
        toggle=request_body.get("toggle"),
        scenario=request_body.get("scenario"),
    )

    mode = request_body.get("mode", "suggest")
    farmer_crop_name = request_body.get("crop")
    farmer_choice_card = None

    if mode == "farmer_led" and farmer_crop_name:
        all_crops_dict = {c["name"]: c for c in crops}
        if farmer_crop_name in all_crops_dict:
            fc = evaluate(all_crops_dict[farmer_crop_name], env)
            fc["verdict"] = verdict(fc)
            farmer_choice_card = _format_card_dict(fc, 1, is_customary=False)
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
                "confidence": {"level": "low", "reason": "Crop data not in regional catalog"},
                "robustness": {"worst_case_total": None, "holds_up_best": False},
                "text": {
                    "why": "We do not have regional agronomic baselines for this cultivar yet.",
                    "risks": "Verify local suitability with an agricultural extension officer.",
                    "previous_crop_effect": "",
                    "next_step": "Tap 'Get Help' to consult a mentor.",
                    "watch_for": "",
                    "after_this": "",
                },
                "notes": ["Uncataloged crop"],
                "needs_local_review": ["variety traits", "local pest resistance", "irrigation requirement"],
                "explainer_keys": [],
            }

    raw_cards = pick_three(crops, env, customary_crop)
    formatted_cards = []
    for idx, c in enumerate(raw_cards):
        c["verdict"] = verdict(c)
        formatted_cards.append(_format_card_dict(c, idx + 1, is_customary=(idx == 0)))

    # Persist in DB
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO plans (field_id, mode, start_week, toggle, farmer_reason, scenario_json, outlook_json, weights_json, inputs_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            (
                field_id,
                mode,
                start_week,
                request_body.get("toggle"),
                request_body.get("reason"),
                json.dumps(env["scenario"]),
                json.dumps(env["outlook_info"]),
                json.dumps(env["weights"]),
                json.dumps({
                    "start_week": start_week,
                    "stored_mm": env["stored_mm"],
                    "stored_basis": env["stored_basis"],
                }),
            ),
        )
        plan_id = cursor.fetchone()["id"]

        for c in formatted_cards:
            conn.execute(
                """INSERT INTO plan_cards (plan_id, position, is_existing_rotation, crop_id, verdict, total, factors_json, flags_json, confidence_json, text_json)
                   VALUES (?, ?, ?, (SELECT id FROM crops WHERE name = ?), ?, ?, ?, ?, ?, ?)""",
                (
                    plan_id,
                    c["position"],
                    1 if c["is_existing_rotation"] else 0,
                    c["crop"],
                    c["verdict"],
                    c["total"],
                    json.dumps(c["factors"]),
                    json.dumps(c["colors"]),
                    json.dumps(c["confidence"]),
                    json.dumps(c["text"]),
                ),
            )

    return {
        "plan_id": plan_id,
        "outlook": env["outlook_info"],
        "weights": env["weights"],
        "inputs": {
            "start_week": start_week,
            "stored_mm": env["stored_mm"],
            "stored_basis": env["stored_basis"],
        },
        "cards": formatted_cards,
        "farmer_choice_card": farmer_choice_card,
        "chosen_card_id": None,
    }

def rescore_plan_service(plan_id: int, new_scenario: dict, new_toggle: str | None = None) -> dict:
    with get_db() as conn:
        plan_row = dict(conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone())
        field = dict(conn.execute("SELECT * FROM fields WHERE id = ?", (plan_row["field_id"],)).fetchone())
        cards_rows = conn.execute("SELECT * FROM plan_cards WHERE plan_id = ? ORDER BY position ASC", (plan_id,)).fetchall()
        
    crops_dict = {c["name"]: c for c in load_crops()}
    inputs = json.loads(plan_row["inputs_json"]) if plan_row["inputs_json"] else {}
    
    env = build_scoring_environment(
        field=field,
        history=[],
        start_week=plan_row["start_week"],
        next_week=20,
        stored_water_answer="moist",
        toggle=new_toggle or plan_row["toggle"],
        scenario=new_scenario,
    )

    rescored_cards = []
    changes = []

    for cr in cards_rows:
        crop_id_val = cr["crop_id"]
        # Lookup name
        with get_db() as conn:
            c_row = conn.execute("SELECT name FROM crops WHERE id = ?", (crop_id_val,)).fetchone()
            crop_name = c_row["name"] if c_row else "paddy"

        if crop_name in crops_dict:
            ev = evaluate(crops_dict[crop_name], env)
            ev["verdict"] = verdict(ev)
            formatted = _format_card_dict(ev, cr["position"], is_customary=bool(cr["is_existing_rotation"]))
            rescored_cards.append(formatted)

            # Detect significant factor changes (> 10 points)
            old_factors = json.loads(cr["factors_json"])
            for f_key, old_v in old_factors.items():
                new_v = formatted["factors"].get(f_key, old_v)
                if abs(new_v - old_v) >= 10:
                    changes.append({
                        "crop": crop_name,
                        "factor": f_key,
                        "from": old_v,
                        "to": new_v,
                        "message_key": FACTOR_TO_MESSAGE.get(f_key, "arrange_irrigation"),
                    })

    return {
        "cards": rescored_cards,
        "changes": changes,
    }

def _format_card_dict(ev: dict, position: int, is_customary: bool) -> dict:
    narrative = get_template_narrative(ev["crop"], ev.get("verdict", "Feasible"), ev["factors"])
    notes = []
    if ev["factors"].get("water", 100) < 40:
        notes.append("Severe water deficit expected during key vegetative window")
    if ev["factors"].get("rotation", 100) < 40:
        notes.append("Expect higher fertilizer and pest-control cost from family repetition")

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
            "worst_case_total": ev.get("worst", ev["total"] - 10.0),
            "holds_up_best": ev.get("holds_up_best", False),
        },
        "text": narrative,
        "notes": notes,
        "needs_local_review": needs_review,
        "explainer_keys": ["water_balance", "rotation", "confidence"],
    }
