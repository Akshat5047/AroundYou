import re

from fastapi import (
    APIRouter,
    HTTPException
)

from schemas.agent import (
    TripPlanRequest,
    TripPlanResponse
)

from agent.trip_agent import plan_trip

from services.trip_storage_service import (
    save_trip_request,
    save_trip_result,
    storage_configured
)


router = APIRouter(
    prefix="/api/agent",
    tags=["AI Agent"]
)


# ============================================================
# DURATION EXTRACTION
# ============================================================

def extract_duration_days(
    text
):
    if not text:
        return None

    match = re.search(
        r"(\d+)\s*[- ]?\s*day",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    try:
        return int(
            match.group(1)
        )

    except (
        ValueError,
        TypeError
    ):
        return None


# ============================================================
# PLAN TRIP
# ============================================================

@router.post(
    "/plan-trip",
    response_model=TripPlanResponse
)
def create_trip_plan(
    request: TripPlanRequest
):
    try:

        # ----------------------------------------------------
        # 1. GENERATE TRIP
        # ----------------------------------------------------

        result = plan_trip(
            user_request=request.request,
            district=request.district,
            travel_date=request.travel_date,
            budget_limit=request.budget_limit,
            num_travelers=request.num_travelers,
            accommodation_tier=(
                request.accommodation_tier
            ),
            transport_mode=(
                request.transport_mode
            ),
            route_distance_km=(
                request.route_distance_km
            ),
            rainfall_mm=(
                request.rainfall_mm
            ),
            road_access_rating=(
                request.road_access_rating
            ),
            festival=request.festival
        )


        # ----------------------------------------------------
        # 2. SUPABASE STORAGE
        #
        # Storage is intentionally non-blocking.
        # A database problem must NOT stop the AI planner.
        # ----------------------------------------------------

        storage_info = {
            "configured": (
                storage_configured()
            ),
            "request_saved": False,
            "result_saved": False,
            "request_id": None,
            "error": None
        }


        if storage_configured():

            try:

                duration_days = (
                    result
                    .get(
                        "tool_results",
                        {}
                    )
                    .get(
                        "requirements",
                        {}
                    )
                    .get(
                        "duration_days"
                    )
                )

                if duration_days is None:
                    duration_days = (
                        extract_duration_days(
                            request.request
                        )
                    )


                # --------------------------------------------
                # SAVE USER REQUEST
                # --------------------------------------------

                saved_request = (
                    save_trip_request(
                        request=request,
                        duration_days=(
                            duration_days
                        )
                    )
                )


                if saved_request:

                    request_id = (
                        saved_request.get(
                            "request_id"
                        )
                    )

                    storage_info[
                        "request_id"
                    ] = request_id

                    storage_info[
                        "request_saved"
                    ] = True


                    # ----------------------------------------
                    # SAVE AI RESULT
                    # ----------------------------------------

                    if request_id is not None:

                        saved_result = (
                            save_trip_result(
                                request_id=(
                                    request_id
                                ),
                                request=request,
                                agent_result=result
                            )
                        )

                        if saved_result:

                            storage_info[
                                "result_saved"
                            ] = True


            except Exception as storage_error:

                storage_info[
                    "error"
                ] = str(
                    storage_error
                )


        # ----------------------------------------------------
        # 3. ADD STORAGE INFORMATION TO TOOL RESULTS
        # ----------------------------------------------------

        if "tool_results" not in result:
            result["tool_results"] = {}

        result[
            "tool_results"
        ][
            "storage"
        ] = storage_info


        # ----------------------------------------------------
        # 4. RETURN NORMAL AGENT RESPONSE
        # ----------------------------------------------------

        return result


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )