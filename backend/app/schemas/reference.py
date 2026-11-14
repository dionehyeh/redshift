from pydantic import BaseModel


class CropSummary(BaseModel):
    id: str
    name: dict[str, str]
    family: str
    duration_days: int
    water_need: str
    market: str

class ExplainerCard(BaseModel):
    key: str
    title: str
    body: str
    lang: str = "en"
    reviewed_by: str | None = None

class SeasonalOutlookResponse(BaseModel):
    region: str
    label: str
    factor_range: list[float]
    source: str
    valid_for: str
    entered_on: str

class SeasonWindow(BaseModel):
    key: str
    name: dict[str, str]
    start_week: int
    end_week: int
    description: str | None = None

class DataSourceItem(BaseModel):
    name: str
    used_for: str
    resolution: str
    latency: str
    limits: str
