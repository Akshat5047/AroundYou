from fastapi import APIRouter, HTTPException

from schemas.agent import (
    TripPlanRequest,
    TripPlanResponse
)

from agent.trip_agent import plan_trip


router = APIRouter(
    prefix="/api/agent",
    tags=["AI Agent"]
)


@router.post(
    "/plan-trip",
    response_model=TripPlanResponse
)
def create_trip_plan(
    request: TripPlanRequest
):

    try:

        return plan_trip(
            user_request=request.request,
            district=request.district,
            travel_date=request.travel_date,
            budget_limit=request.budget_limit,
            num_travelers=request.num_travelers,
            accommodation_tier=request.accommodation_tier,
            transport_mode=request.transport_mode,
            route_distance_km=request.route_distance_km,
            rainfall_mm=request.rainfall_mm,
            road_access_rating=request.road_access_rating,
            festival=request.festival
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )