import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_DIR / ".env"
)

SUPABASE_URL = os.getenv(
    "SUPABASE_URL",
    ""
).rstrip("/")

SUPABASE_KEY = os.getenv(
    "SUPABASE_KEY",
    ""
)


# ============================================================
# HELPERS
# ============================================================

def storage_configured():
    return bool(
        SUPABASE_URL
        and SUPABASE_KEY
    )


def _headers(prefer="return=representation"):
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _post_row(
    table_name,
    payload
):
    if not storage_configured():
        raise RuntimeError(
            "Supabase storage is not configured."
        )

    url = (
        f"{SUPABASE_URL}"
        f"/rest/v1/{table_name}"
    )

    data = json.dumps(
        payload,
        default=str
    ).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=_headers(),
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=15
        ) as response:

            body = (
                response.read()
                .decode("utf-8")
            )

            if not body:
                return None

            result = json.loads(body)

            if (
                isinstance(result, list)
                and result
            ):
                return result[0]

            return result

    except urllib.error.HTTPError as error:

        body = (
            error.read()
            .decode(
                "utf-8",
                errors="replace"
            )
        )

        raise RuntimeError(
            f"Supabase returned "
            f"HTTP {error.code}: {body}"
        ) from error

    except urllib.error.URLError as error:

        raise RuntimeError(
            f"Could not connect to Supabase: "
            f"{error.reason}"
        ) from error


def _safe_number(
    data,
    possible_keys
):
    if not isinstance(
        data,
        dict
    ):
        return None

    for key in possible_keys:

        value = data.get(key)

        if isinstance(
            value,
            (int, float)
        ):
            return value

    return None


def _get_destination(
    agent_result
):
    try:
        sources = (
            agent_result
            .get("tool_results", {})
            .get("destination_search", {})
            .get("sources", [])
        )

        if sources:
            return sources[0]

    except Exception:
        pass

    return {}


def _get_ml_results(
    agent_result
):
    return (
        agent_result
        .get("tool_results", {})
        .get("ml_predictions", {})
    )


def _get_budget_evaluation(
    agent_result
):
    return (
        agent_result
        .get("tool_results", {})
        .get("budget_evaluation", {})
    )


def _get_generation(
    agent_result
):
    return (
        agent_result
        .get("tool_results", {})
        .get("generation", {})
    )


# ============================================================
# SAVE REQUEST
# ============================================================

def save_trip_request(
    request,
    duration_days=None
):
    """
    Save the user's planner inputs before the AI result
    is persisted.

    Existing SmartYatra columns are reused where possible.
    """

    budget_level = (
        request.accommodation_tier
        if request.accommodation_tier
        else None
    )

    payload = {
        "district": request.district,
        "number_of_travelers": (
            request.num_travelers
        ),
        "start_date": (
            request.travel_date
        ),
        "budget_level": budget_level,
        "budget_amount": (
            request.budget_limit
        ),

        "duration_days": duration_days,

        "accommodation_tier": (
            request.accommodation_tier
        ),

        "transport_mode": (
            request.transport_mode
        ),

        "route_distance_km": (
            request.route_distance_km
        ),

        "rainfall_mm": (
            request.rainfall_mm
        ),

        "road_access_rating": (
            request.road_access_rating
        ),

        "festival": request.festival,

        "user_request": request.request,
    }

    # Remove None values so nullable/default database
    # columns can behave normally.
    payload = {
        key: value
        for key, value
        in payload.items()
        if value is not None
    }

    return _post_row(
        "trip_requests",
        payload
    )


# ============================================================
# SAVE RESULT
# ============================================================

def save_trip_result(
    request_id,
    request,
    agent_result
):
    destination = _get_destination(
        agent_result
    )

    ml_results = _get_ml_results(
        agent_result
    )

    budget_evaluation = (
        _get_budget_evaluation(
            agent_result
        )
    )

    generation = _get_generation(
        agent_result
    )

    requirements = (
        agent_result
        .get("tool_results", {})
        .get("requirements", {})
    )

    # --------------------------------------------------------
    # Budget
    # --------------------------------------------------------

    predicted_budget = (
        budget_evaluation.get(
            "predicted_cost"
        )
    )

    difference = (
        budget_evaluation.get(
            "difference"
        )
    )

    remaining_budget = None

    if isinstance(
        difference,
        (int, float)
    ):
        remaining_budget = difference

    # --------------------------------------------------------
    # Crowd
    # --------------------------------------------------------

    crowd_result = (
        ml_results.get(
            "crowd",
            {}
        )
    )

    crowd_prediction = (
        crowd_result.get(
            "prediction",
            {}
        )
    )

    predicted_crowd = _safe_number(
        crowd_prediction,
        [
            "predicted_total_visitors",
            "predicted_visitors",
            "visitor_count"
        ]
    )

    # --------------------------------------------------------
    # Climate
    # --------------------------------------------------------

    climate_result = (
        ml_results.get(
            "climate",
            {}
        )
    )

    climate_text = json.dumps(
        climate_result,
        default=str
    )

    # --------------------------------------------------------
    # Transport ML recommendation
    # --------------------------------------------------------

    transport_result = (
        ml_results.get(
            "transport",
            {}
        )
    )

    transport_prediction = (
        transport_result.get(
            "prediction",
            {}
        )
    )

    recommended_transport = None

    if isinstance(
        transport_prediction,
        dict
    ):
        recommended_transport = (
            transport_prediction.get(
                "recommended_transport_mode"
            )
            or transport_prediction.get(
                "transport_mode"
            )
            or transport_prediction.get(
                "prediction"
            )
        )

    # --------------------------------------------------------
    # Destination context
    # --------------------------------------------------------

    destination_context = (
        destination.get("content")
        if destination
        else None
    )

    # --------------------------------------------------------
    # Result payload
    # --------------------------------------------------------

    payload = {
        "request_id": request_id,

        "district": (
            request.district
            or destination.get("district")
        ),

        "travel_date": (
            request.travel_date
        ),

        "duration_days": (
            requirements.get(
                "duration_days"
            )
        ),

        "destination": (
            destination.get(
                "spot_name"
            )
        ),

        "destination_context": (
            destination_context
        ),

        "predicted_budget": (
            predicted_budget
        ),

        "remaining_budget": (
            remaining_budget
        ),

        "predicted_crowd": (
            predicted_crowd
        ),

        "climate_result": (
            climate_text
        ),

        "ai_plan": (
            agent_result.get(
                "plan"
            )
        ),

        "generation_mode": (
            generation.get(
                "mode"
            )
        ),

        # Existing SmartYatra trip_results columns
        "distance_km": (
            request.route_distance_km
        ),

        "budget_limit": (
            request.budget_limit
        ),

        "num_people": (
            request.num_travelers
        ),

        "rainfall_mm": (
            request.rainfall_mm
        ),

        "road_access_rating": (
            request.road_access_rating
        ),

        "recommended_transport_mode": (
            recommended_transport
        ),
    }

    payload = {
        key: value
        for key, value
        in payload.items()
        if value is not None
    }

    return _post_row(
        "trip_results",
        payload
    )