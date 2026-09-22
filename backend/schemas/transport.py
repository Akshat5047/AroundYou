from pydantic import BaseModel


class TransportInput(BaseModel):
    distance_km: float
    budget_limit: float
    num_people: int
    rainfall_mm: float
    road_access_rating: int