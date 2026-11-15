import json

from fastapi import APIRouter, Depends

from app.db import get_db
from app.deps import own_field, own_plan, require_role
from app.errors import AppError
from app.schemas.plans import (
    PlanChooseRequest,
    PlanCreateRequest,
    RescoreRequest,
    RescoreResponse,
)
from app.services.plan_service import (
    create_plan_service,
    rescore_plan_service,
    upcoming_week_start,
)

router = APIRouter(tags=["Crop Plans & Simulation"])

@router.post("/fields/{field_id}/plans", status_code=201)
def create_plan(field_id: int, body: PlanCreateRequest, user: dict = Depends(require_role("farmer")), field: dict = Depends(own_field)):
    if field.get("profile_status") != "ready":
        raise AppError("FIELD_NOT_READY", "Field profile is still building", status=409, details={"field_id": field_id})
    if body.mode == "farmer_led" and not body.crop:
        raise AppError("CROP_REQUIRED", "Farmer-led mode requires naming a target crop", status=422)

    return create_plan_service(field_id, body.model_dump())

@router.get("/plans/{id}")
def get_plan(id: int, user: dict = Depends(require_role("farmer")), plan: dict = Depends(own_plan)):
    with get_db() as conn:
        plan_row = plan
        
        cards_rows = conn.execute(
            """SELECT pc.*, c.name AS crop_name
               FROM plan_cards pc
               LEFT JOIN crops c ON pc.crop_id = c.id
               WHERE pc.plan_id = ? ORDER BY pc.position ASC""",
            (id,),
        ).fetchall()
        cards = []
        for c in cards_rows:
            if not c["crop_name"]:
                raise AppError(
                    "PLAN_CARD_CROP_UNAVAILABLE",
                    "A crop in this plan is no longer available",
                    status=409,
                    details={"plan_id": id, "card_id": c["position"]},
                )
            evidence = json.loads(c["evidence_json"]) if c["evidence_json"] else {}
            cards.append({
                "id": c["position"],
                "position": c["position"],
                "is_existing_rotation": bool(c["is_existing_rotation"]),
                "crop": c["crop_name"],
                "verdict": c["verdict"],
                "total": c["total"],
                "factors": json.loads(c["factors_json"]),
                "colors": json.loads(c["flags_json"]),
                "confidence": json.loads(c["confidence_json"]),
                "robustness": (
                    json.loads(c["robustness_json"])
                    if c["robustness_json"]
                    else {"worst_case_total": None, "holds_up_best": False}
                ),
                "text": json.loads(c["text_json"]),
                "notes": json.loads(c["notes_json"]) if c["notes_json"] else [],
                "needs_local_review": evidence.get("needs_local_review", []),
                "explainer_keys": evidence.get("explainer_keys", []),
            })

        inputs = json.loads(plan_row["inputs_json"]) if plan_row["inputs_json"] else {}
        return {
            "plan_id": id,
            "outlook": json.loads(plan_row["outlook_json"]),
            "weights": json.loads(plan_row["weights_json"]),
            "inputs": inputs,
            "cards": cards,
            "farmer_choice_card": inputs.get("farmer_choice_card"),
            "chosen_card_id": plan_row["chosen_card_id"],
        }

@router.post("/plans/{id}/rescore", response_model=RescoreResponse)
def rescore_plan(
    id: int,
    body: RescoreRequest,
    user: dict = Depends(require_role("farmer")),
    plan: dict = Depends(own_plan),
):
    return rescore_plan_service(id, body.scenario.model_dump(), body.toggle)

@router.post("/plans/{id}/choose")
def choose_card(
    id: int,
    body: PlanChooseRequest,
    user: dict = Depends(require_role("farmer")),
    plan: dict = Depends(own_plan),
):
    with get_db() as conn:
        card = conn.execute("SELECT * FROM plan_cards WHERE plan_id = ? AND position = ?", (id, body.card_id)).fetchone()
        if not card:
            raise AppError("NOT_FOUND", "Plan card not found", status=404)
        
        conn.execute("UPDATE plans SET chosen_card_id = ? WHERE id = ?", (body.card_id, id))
        start_date = upcoming_week_start(plan["start_week"]).isoformat()
        cursor = conn.execute(
            """INSERT INTO seasons (field_id, crop_id, status, start_date)
               VALUES (?, ?, 'planned', ?) RETURNING id""",
            (plan["field_id"], card["crop_id"], start_date),
        )
        season_id = cursor.fetchone()["id"]
        conn.execute(
            """INSERT INTO audit_log (user_id, action, object_type, object_id)
               VALUES (?, 'CHOOSE_PLAN_CARD', 'plan', ?)""",
            (user["id"], id),
        )

    return {"status": "planned", "season_id": season_id, "card_id": body.card_id}
