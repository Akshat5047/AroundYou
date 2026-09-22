from fastapi import APIRouter

from schemas.review import ReviewInput
from services.review_service import classify_review


router = APIRouter(
    prefix="/api/reviews",
    tags=["Review Trust"]
)


@router.post("/classify")
def review_classification(data: ReviewInput):

    return classify_review(
        data.review
    )