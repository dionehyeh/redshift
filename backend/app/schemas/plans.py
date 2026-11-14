from typing import Literal
from pydantic import BaseModel, Field

class ScenarioModel(BaseModel):
    rain: float = Field(1.0, ge=0.5, le=1.5)
    temp: float = Field(0.0, ge=-3.0, le=5.0)

class PlanCreateRequest(BaseModel):
    mode: Literal["suggest", "farmer_led"] = "suggest"
    start_week: int | None = Field(None, ge=1, le=52)
    season: Literal["virippu", "mundakan", "puncha"] | None = None
    crop: str | None = None
    reason: Literal["market", "finance", "other"] | None = None
    toggle: Literal["earn_more", "play_safe"] | None = None
    stored_water_answer: Literal["dry", "moist", "wet"] | None = None
    scenario: ScenarioModel = ScenarioModel()

class RescoreRequest(BaseModel):
    scenario: ScenarioModel
    toggle: Literal["earn_more", "play_safe"] | None = None

class PlanChooseRequest(BaseModel):
    card_id: int

class ConfidenceDetail(BaseModel):
    level: str
    reason: str

class RobustnessDetail(BaseModel):
    worst_case_total: float | None = None
    holds_up_best: bool = False

class CardNarrative(BaseModel):
    why: str = ""
    risks: str = ""
    previous_crop_effect: str = ""
    next_step: str = ""
    watch_for: str = ""
    after_this: str = ""

class PlanCardResponse(BaseModel):
    id: int
    position: int
    is_existing_rotation: bool = False
    crop: str
    verdict: str
    total: float | None = None
    factors: dict[str, float] = {}
    colors: dict[str, str] = {}
    confidence: ConfidenceDetail
    robustness: RobustnessDetail
    text: CardNarrative
    notes: list[str] = []
    needs_local_review: list[str] = []
    explainer_keys: list[str] = []

class FactorChangeItem(BaseModel):
    crop: str
    factor: str
    from_: float = Field(..., alias="from")
    to: float
    message_key: str | None = None

class RescoreResponse(BaseModel):
    cards: list[PlanCardResponse]
    changes: list[FactorChangeItem] = []

class PlanResponse(BaseModel):
    plan_id: int
    outlook: dict
    weights: dict[str, float]
    inputs: dict
    cards: list[PlanCardResponse]
    farmer_choice_card: PlanCardResponse | None = None
    chosen_card_id: int | None = None
