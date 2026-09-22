from pydantic import BaseModel


class ClimateInput(BaseModel):
    district: str
    forecast_date: str