from fastapi import APIRouter

from schemas.crowd import CrowdInput
from services.crowd_service import predict_crowd


router = APIRouter(
    prefix="/api/crowd",
    tags=["Crowd"]
)


@router.post("/predict")
def crowd_prediction(data: CrowdInput):

    return predict_crowd(
        data.model_dump()
    )