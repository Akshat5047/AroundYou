from pydantic import BaseModel


class CrowdInput(BaseModel):
    spot_name: str
    district: str
    category: str
    year: int
    month: str
    season: str
    festival: str