from fastapi import APIRouter

from schemas.transport import TransportInput
from services.transport_service import predict_transport


router = APIRouter(
    prefix="/api/transport",
    tags=["Transport"]
)


@router.post("/predict")
def transport_prediction(data: TransportInput):

    return predict_transport(
        data.model_dump()
    )