from fastapi import APIRouter

from schemas.climate import ClimateInput
from services.climate_service import predict_climate


router = APIRouter(
    prefix="/api/climate",
    tags=["Climate"]
)


@router.post("/predict")
def climate_prediction(data: ClimateInput):

    return predict_climate(
        data.model_dump()
    )