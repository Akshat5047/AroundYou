from pydantic import BaseModel, Field


class ReviewInput(BaseModel):
    review: str = Field(
        ...,
        min_length=3,
        description="Review text to classify"
    )