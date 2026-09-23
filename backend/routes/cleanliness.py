import base64

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)

from services.cleanliness_service import (
    analyze_cleanliness,
)


router = APIRouter(
    prefix="/api/cleanliness",
    tags=["Cleanliness"],
)


ALLOWED_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/analyze")
async def analyze_uploaded_image(
    file: UploadFile = File(...),
):
    if (
        file.content_type
        and file.content_type
        not in ALLOWED_TYPES
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported image type. "
                "Use JPEG, PNG, or WebP."
            ),
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty.",
        )

    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="Image must be smaller than 10 MB.",
        )

    try:
        result = analyze_cleanliness(
            image_bytes
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Cleanliness analysis failed: "
                f"{exc}"
            ),
        ) from exc

    annotated_base64 = base64.b64encode(
        result["annotated_image"]
    ).decode("utf-8")

    return {
        "cleanliness_score": (
            result["cleanliness_score"]
        ),
        "status": result["status"],
        "litter_count": (
            result["litter_count"]
        ),
        "detections": (
            result["detections"]
        ),
        "annotated_image": (
            "data:image/jpeg;base64,"
            + annotated_base64
        ),
        "disclaimer": (
            result["disclaimer"]
        ),
    }