from typing import Optional
from pydantic import BaseModel, Field


class TripPlanRequest(BaseModel):
    request: str = Field(
        ...,
        min_length=3,
        description="Natural-language trip planning request"
    )

    district: Optional[str] = None
    travel_date: Optional[str] = None

    budget_limit: Optional[float] = None
    num_travelers: Optional[int] = None

    accommodation_tier: Optional[str] = None
    transport_mode: Optional[str] = None

    route_distance_km: Optional[float] = None
    rainfall_mm: Optional[float] = None
    road_access_rating: Optional[int] = None

    festival: Optional[str] = None


class TripPlanResponse(BaseModel):
    request: str
    plan: str
    tools_used: list[str]
    tool_results: dict