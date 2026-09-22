from pydantic import BaseModel


class BudgetInput(BaseModel):
    duration_days: int
    num_travelers: int
    route_distance_km: float
    accommodation_tier: str
    transport_mode: str
    season: str