from fastapi import APIRouter

from schemas.budget import BudgetInput
from services.budget_service import predict_budget


router = APIRouter(
    prefix="/api/budget",
    tags=["Budget"]
)


@router.post("/predict")
def budget_prediction(data: BudgetInput):

    return predict_budget(
        data.model_dump()
    )