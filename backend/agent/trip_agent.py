import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from agent.tools import (
    search_destination_knowledge,
    run_budget_prediction,
    run_climate_prediction,
    run_crowd_prediction,
    run_transport_prediction
)


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_DIR = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_DIR / ".env"
)

API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

client = None

if API_KEY:

    client = genai.Client(
        api_key=API_KEY
    )


MODEL_NAME = "gemini-3.6-flash"


# ============================================================
# BASIC REQUEST EXTRACTION
# ============================================================

def extract_duration(text):

    match = re.search(
        r"(\d+)\s*[- ]?\s*day",
        text,
        re.IGNORECASE
    )

    if match:
        return int(
            match.group(1)
        )

    return None


def extract_travelers(text):

    patterns = [
        r"for\s+(\d+)\s+people",
        r"for\s+(\d+)\s+persons?",
        r"for\s+(\d+)\s+travelers?",
        r"(\d+)\s+people",
        r"(\d+)\s+travelers?"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return int(
                match.group(1)
            )

    return None


def extract_budget(text):

    patterns = [
        r"₹\s*([\d,]+)",
        r"rs\.?\s*([\d,]+)",
        r"inr\s*([\d,]+)",
        r"budget\s+(?:of\s+)?([\d,]+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            value = (
                match.group(1)
                .replace(",", "")
            )

            return float(value)

    return None


def extract_transport(text):

    text_lower = text.lower()

    modes = [
        "bus",
        "car",
        "auto",
        "bike"
    ]

    for mode in modes:

        if mode in text_lower:
            return mode

    return None


def extract_accommodation(text):

    text_lower = text.lower()

    if (
        "budget hotel" in text_lower
        or "cheap hotel" in text_lower
        or "budget accommodation" in text_lower
    ):
        return "Budget"

    if (
        "mid-range" in text_lower
        or "mid range" in text_lower
    ):
        return "Mid-range"

    if (
        "luxury" in text_lower
        or "premium hotel" in text_lower
    ):
        return "Luxury"

    return None


def extract_interests(text):

    text_lower = text.lower()

    known_interests = {
        "temple": "Temples",
        "kakatiya": "Kakatiya heritage",
        "fort": "Forts",
        "museum": "Museums",
        "history": "History",
        "historical": "History",
        "architecture": "Architecture",
        "sculpture": "Sculptures",
        "lake": "Lakes",
        "waterfall": "Waterfalls",
        "pilgrimage": "Pilgrimage"
    }

    interests = []

    for keyword, label in (
        known_interests.items()
    ):

        if (
            keyword in text_lower
            and label not in interests
        ):

            interests.append(
                label
            )

    return interests


# ============================================================
# REQUEST UNDERSTANDING
# ============================================================

def understand_request(
    user_request,
    district=None,
    travel_date=None,
    budget_limit=None,
    num_travelers=None,
    accommodation_tier=None,
    transport_mode=None
):

    return {
        "destination_or_district": district,

        "travel_date": travel_date,

        "duration_days": extract_duration(
            user_request
        ),

        "num_travelers": (
            num_travelers
            if num_travelers is not None
            else extract_travelers(
                user_request
            )
        ),

        "budget_limit": (
            budget_limit
            if budget_limit is not None
            else extract_budget(
                user_request
            )
        ),

        "accommodation_tier": (
            accommodation_tier
            if accommodation_tier is not None
            else extract_accommodation(
                user_request
            )
        ),

        "transport_mode": (
            transport_mode
            if transport_mode is not None
            else extract_transport(
                user_request
            )
        ),

        "interests": extract_interests(
            user_request
        ),

        "preferences": []
    }


# ============================================================
# SEASON
# ============================================================

def get_season(
    travel_date
):

    if not travel_date:
        return None

    try:

        date = datetime.strptime(
            travel_date,
            "%Y-%m-%d"
        )

    except (
        ValueError,
        TypeError
    ):

        return None

    month = date.month

    if month in [
        3,
        4,
        5
    ]:
        return "Summer"

    if month in [
        6,
        7,
        8,
        9
    ]:
        return "Monsoon"

    return "Winter"


# ============================================================
# SERVICE RESULT VALIDATION
# ============================================================

def service_succeeded(
    result
):

    if result is None:
        return False

    if not isinstance(
        result,
        dict
    ):
        return True

    if result.get("error"):
        return False

    return True


def service_error_message(
    result
):

    if isinstance(result, dict):

        if result.get("error"):
            return str(
                result["error"]
            )

    return (
        "Prediction service returned "
        "an invalid result."
    )


# ============================================================
# DESTINATION RELEVANCE
# ============================================================

def destination_interest_score(
    source,
    interests
):

    text = " ".join([
        str(
            source.get(
                "spot_name",
                ""
            )
        ),
        str(
            source.get(
                "category",
                ""
            )
        ),
        str(
            source.get(
                "content",
                ""
            )
        )
    ]).lower()

    score = 0

    interest_keywords = {
        "Temples": [
            "temple",
            "pilgrimage"
        ],

        "Kakatiya heritage": [
            "kakatiya"
        ],

        "Forts": [
            "fort"
        ],

        "Museums": [
            "museum",
            "gallery"
        ],

        "History": [
            "historic",
            "historical",
            "heritage"
        ],

        "Architecture": [
            "architecture",
            "architectural"
        ],

        "Sculptures": [
            "sculpture",
            "sculptural"
        ],

        "Lakes": [
            "lake"
        ],

        "Waterfalls": [
            "waterfall"
        ],

        "Pilgrimage": [
            "pilgrimage",
            "temple"
        ]
    }

    for interest in interests:

        keywords = interest_keywords.get(
            interest,
            []
        )

        for keyword in keywords:

            if keyword in text:
                score += 1

    return score


def filter_destination_results(
    destination_result,
    requirements
):

    all_sources = destination_result.get(
        "sources",
        []
    )

    requested_district = requirements.get(
        "destination_or_district"
    )

    interests = requirements.get(
        "interests",
        []
    )

    # --------------------------------------------------------
    # FIRST PRIORITY:
    # Explicitly requested district
    # --------------------------------------------------------

    district_sources = []

    if requested_district:

        requested_lower = (
            requested_district
            .strip()
            .lower()
        )

        district_sources = [
            source
            for source in all_sources
            if str(
                source.get(
                    "district",
                    ""
                )
            ).strip().lower()
            == requested_lower
        ]

    # --------------------------------------------------------
    # SECOND PRIORITY:
    # Interest relevance
    # --------------------------------------------------------

    ranked_sources = []

    source_pool = (
        district_sources
        if district_sources
        else all_sources
    )

    for source in source_pool:

        interest_score = (
            destination_interest_score(
                source,
                interests
            )
        )

        similarity = float(
            source.get(
                "similarity",
                0
            )
        )

        ranked_sources.append(
            (
                interest_score,
                similarity,
                source
            )
        )

    ranked_sources.sort(
        key=lambda item: (
            item[0],
            item[1]
        ),
        reverse=True
    )

    filtered = [
        item[2]
        for item in ranked_sources
    ]

    # If interests were supplied, prefer results
    # that actually match at least one interest.

    if interests:

        matching = [
            item[2]
            for item in ranked_sources
            if item[0] > 0
        ]

        if matching:
            filtered = matching

    # Return maximum 3 clean results.

    return {
        "query": destination_result.get(
            "query",
            ""
        ),
        "sources": filtered[:3]
    }


# ============================================================
# DESTINATION RETRIEVAL
# ============================================================

def run_destination_search(
    requirements
):

    parts = []

    destination = requirements.get(
        "destination_or_district"
    )

    interests = requirements.get(
        "interests",
        []
    )

    if destination:

        parts.append(
            f"Tourist destinations in "
            f"{destination}."
        )

    if interests:

        parts.append(
            "Traveler interests: "
            + ", ".join(interests)
            + "."
        )

    if not parts:

        parts.append(
            "Tourist destinations in Telangana."
        )

    query = " ".join(
        parts
    )

    raw_result = (
        search_destination_knowledge(
            query=query,
            top_k=10
        )
    )

    return filter_destination_results(
        raw_result,
        requirements
    )


# ============================================================
# ML ORCHESTRATION
# ============================================================

def run_ml_tools(
    requirements,
    destination_result,
    route_distance_km=None,
    rainfall_mm=None,
    road_access_rating=None,
    festival=None
):

    results = {}

    sources = destination_result.get(
        "sources",
        []
    )

    travel_date = requirements.get(
        "travel_date"
    )

    duration_days = requirements.get(
        "duration_days"
    )

    num_travelers = requirements.get(
        "num_travelers"
    )

    budget_limit = requirements.get(
        "budget_limit"
    )

    accommodation_tier = requirements.get(
        "accommodation_tier"
    )

    planned_transport = requirements.get(
        "transport_mode"
    )

    district = requirements.get(
        "destination_or_district"
    )

    if not district and sources:

        district = sources[0].get(
            "district"
        )

    season = get_season(
        travel_date
    )

    # ========================================================
    # CLIMATE
    # ========================================================

    missing = []

    if not district:
        missing.append(
            "district"
        )

    if not travel_date:
        missing.append(
            "travel_date"
        )

    if missing:

        results["climate"] = {
            "status": "not_run",
            "missing_fields": missing
        }

    else:

        try:

            prediction = (
                run_climate_prediction(
                    district=district,
                    forecast_date=travel_date
                )
            )

            if service_succeeded(
                prediction
            ):

                results["climate"] = {
                    "status": "success",
                    "prediction": prediction
                }

            else:

                results["climate"] = {
                    "status": "error",
                    "message": (
                        service_error_message(
                            prediction
                        )
                    )
                }

        except Exception as error:

            results["climate"] = {
                "status": "error",
                "message": str(error)
            }

    # ========================================================
    # BUDGET
    # ========================================================

    budget_values = {
        "duration_days": duration_days,
        "num_travelers": num_travelers,
        "route_distance_km": route_distance_km,
        "accommodation_tier": accommodation_tier,
        "transport_mode": planned_transport,
        "season": season
    }

    missing = [
        key
        for key, value
        in budget_values.items()
        if value is None
    ]

    if missing:

        results["budget"] = {
            "status": "not_run",
            "missing_fields": missing
        }

    else:

        try:

            prediction = (
                run_budget_prediction(
                    **budget_values
                )
            )

            if service_succeeded(
                prediction
            ):

                results["budget"] = {
                    "status": "success",

                    "planned_transport_mode": (
                        planned_transport
                    ),

                    "prediction": prediction
                }

            else:

                results["budget"] = {
                    "status": "error",
                    "message": (
                        service_error_message(
                            prediction
                        )
                    )
                }

        except Exception as error:

            results["budget"] = {
                "status": "error",
                "message": str(error)
            }

    # ========================================================
    # TRANSPORT RECOMMENDATION
    # ========================================================

    transport_values = {
        "distance_km": route_distance_km,
        "budget_limit": budget_limit,
        "num_people": num_travelers,
        "rainfall_mm": rainfall_mm,
        "road_access_rating": road_access_rating
    }

    missing = [
        key
        for key, value
        in transport_values.items()
        if value is None
    ]

    if missing:

        results["transport"] = {
            "status": "not_run",
            "missing_fields": missing
        }

    else:

        try:

            prediction = (
                run_transport_prediction(
                    **transport_values
                )
            )

            if service_succeeded(
                prediction
            ):

                results["transport"] = {
                    "status": "success",

                    "user_planned_mode": (
                        planned_transport
                    ),

                    "prediction": prediction
                }

            else:

                results["transport"] = {
                    "status": "error",
                    "message": (
                        service_error_message(
                            prediction
                        )
                    )
                }

        except Exception as error:

            results["transport"] = {
                "status": "error",
                "message": str(error)
            }

    # ========================================================
    # CROWD
    # ========================================================

    if not sources:

        results["crowd"] = {
            "status": "not_run",
            "missing_fields": [
                "destination"
            ]
        }

    elif not travel_date:

        results["crowd"] = {
            "status": "not_run",
            "missing_fields": [
                "travel_date"
            ]
        }

    else:

        try:

            source = sources[0]

            date = datetime.strptime(
                travel_date,
                "%Y-%m-%d"
            )

            prediction = (
                run_crowd_prediction(
                    spot_name=source[
                        "spot_name"
                    ],
                    district=source[
                        "district"
                    ],
                    category=source[
                        "category"
                    ],
                    year=date.year,
                    month=date.strftime(
                        "%B"
                    ),
                    season=season,
                    festival=(
                        festival
                        if festival
                        else "None"
                    )
                )
            )

            if service_succeeded(
                prediction
            ):

                results["crowd"] = {
                    "status": "success",
                    "destination": source[
                        "spot_name"
                    ],
                    "prediction": prediction
                }

            else:

                results["crowd"] = {
                    "status": "error",
                    "destination": source[
                        "spot_name"
                    ],
                    "message": (
                        service_error_message(
                            prediction
                        )
                    )
                }

        except Exception as error:

            results["crowd"] = {
                "status": "error",
                "message": str(error)
            }

    return results


# ============================================================
# BUDGET CONSTRAINT
# ============================================================

def evaluate_budget(
    ml_results,
    budget_limit
):

    if budget_limit is None:

        return {
            "status": "not_checked",
            "reason": (
                "No budget limit supplied."
            )
        }

    result = ml_results.get(
        "budget",
        {}
    )

    if (
        result.get("status")
        != "success"
    ):

        return {
            "status": "not_checked",
            "reason": (
                "Budget ML prediction "
                "was not available."
            )
        }

    prediction = result.get(
        "prediction",
        {}
    )

    predicted_cost = prediction.get(
        "predicted_total_cost"
    )

    if predicted_cost is None:

        return {
            "status": "not_checked",
            "reason": (
                "Budget model did not "
                "return total cost."
            )
        }

    budget_limit = float(
        budget_limit
    )

    predicted_cost = float(
        predicted_cost
    )

    difference = (
        budget_limit
        - predicted_cost
    )

    return {
        "status": (
            "within_budget"
            if difference >= 0
            else "over_budget"
        ),

        "budget_limit": budget_limit,

        "predicted_cost": predicted_cost,

        "difference": difference
    }


# ============================================================
# SAFE NUMBER HELPER
# ============================================================

def get_number(
    data,
    possible_keys
):

    if not isinstance(
        data,
        dict
    ):
        return None

    for key in possible_keys:

        value = data.get(
            key
        )

        if isinstance(
            value,
            (int, float)
        ):
            return value

    return None


# ============================================================
# FALLBACK PLAN
# ============================================================

def generate_fallback_plan(
    requirements,
    destination_result,
    ml_results,
    budget_evaluation
):

    lines = []

    lines.append(
        "Around You Trip Plan"
    )

    lines.append("")

    duration = requirements.get(
        "duration_days"
    )

    travelers = requirements.get(
        "num_travelers"
    )

    travel_date = requirements.get(
        "travel_date"
    )

    planned_transport = requirements.get(
        "transport_mode"
    )

    if duration:

        lines.append(
            f"Duration: {duration} day(s)"
        )

    if travelers:

        lines.append(
            f"Travelers: {travelers}"
        )

    if travel_date:

        lines.append(
            f"Start date: {travel_date}"
        )

    lines.append("")

    # --------------------------------------------------------
    # DESTINATIONS
    # --------------------------------------------------------

    sources = destination_result.get(
        "sources",
        []
    )

    if sources:

        lines.append(
            "Suggested destinations:"
        )

        destination_limit = (
            duration
            if duration
            else len(sources)
        )

        destination_limit = min(
            destination_limit,
            len(sources)
        )

        for index, source in enumerate(
            sources[:destination_limit],
            start=1
        ):

            lines.append(
                f"{index}. "
                f"{source['spot_name']} "
                f"({source['district']})"
            )

            lines.append(
                f"   {source['content']}"
            )

    else:

        lines.append(
            "No matching destination information "
            "was available in the current "
            "Around You knowledge base."
        )

    lines.append("")

    # --------------------------------------------------------
    # BUDGET
    # --------------------------------------------------------

    lines.append(
        "Budget:"
    )

    budget_status = (
        budget_evaluation.get(
            "status"
        )
    )

    if (
        budget_status
        == "within_budget"
    ):

        predicted = (
            budget_evaluation[
                "predicted_cost"
            ]
        )

        remaining = (
            budget_evaluation[
                "difference"
            ]
        )

        lines.append(
            f"Predicted trip cost: "
            f"₹{predicted:.2f}"
        )

        lines.append(
            f"Estimated remaining budget: "
            f"₹{remaining:.2f}"
        )

    elif (
        budget_status
        == "over_budget"
    ):

        predicted = (
            budget_evaluation[
                "predicted_cost"
            ]
        )

        over_amount = abs(
            budget_evaluation[
                "difference"
            ]
        )

        lines.append(
            f"Predicted trip cost: "
            f"₹{predicted:.2f}"
        )

        lines.append(
            f"The predicted cost exceeds "
            f"your budget by "
            f"₹{over_amount:.2f}."
        )

    else:

        lines.append(
            "Budget prediction could not "
            "be completed with the "
            "available inputs."
        )

    lines.append("")

    # --------------------------------------------------------
    # TRANSPORT
    # --------------------------------------------------------

    lines.append(
        "Transport:"
    )

    if planned_transport:

        lines.append(
            f"Transport selected for budget "
            f"planning: {planned_transport}"
        )

    transport = ml_results.get(
        "transport",
        {}
    )

    if (
        transport.get("status")
        == "success"
    ):

        prediction = transport.get(
            "prediction",
            {}
        )

        mode = (
            prediction.get(
                "recommended_transport_mode"
            )
            or prediction.get(
                "transport_mode"
            )
            or prediction.get(
                "prediction"
            )
        )

        if mode:

            lines.append(
                f"Transport ML recommendation: "
                f"{mode}"
            )

        else:

            lines.append(
                f"Transport model result: "
                f"{prediction}"
            )

    elif (
        transport.get("status")
        == "error"
    ):

        lines.append(
            "Transport recommendation "
            "was unavailable."
        )

    else:

        lines.append(
            "Transport recommendation "
            "was not run because some "
            "required inputs were unavailable."
        )

    lines.append("")

    # --------------------------------------------------------
    # CLIMATE
    # --------------------------------------------------------

    lines.append(
        "Climate:"
    )

    climate = ml_results.get(
        "climate",
        {}
    )

    if (
        climate.get("status")
        == "success"
    ):

        lines.append(
            f"Climate model prediction: "
            f"{climate.get('prediction')}"
        )

    elif (
        climate.get("status")
        == "error"
    ):

        lines.append(
            "Climate prediction is unavailable "
            "for the selected district/date."
        )

    else:

        lines.append(
            "Climate prediction was not run "
            "because required inputs were "
            "unavailable."
        )

    lines.append("")

    # --------------------------------------------------------
    # CROWD
    # --------------------------------------------------------

    lines.append(
        "Crowd:"
    )

    crowd = ml_results.get(
        "crowd",
        {}
    )

    if (
        crowd.get("status")
        == "success"
    ):

        prediction = crowd.get(
            "prediction",
            {}
        )

        visitors = get_number(
            prediction,
            [
                "predicted_total_visitors",
                "predicted_visitors",
                "visitor_count"
            ]
        )

        if visitors is not None:

            lines.append(
                f"Predicted visitors for "
                f"{crowd.get('destination')}: "
                f"{visitors:.0f}"
            )

        else:

            lines.append(
                f"Crowd model result: "
                f"{prediction}"
            )

    elif (
        crowd.get("status")
        == "error"
    ):

        lines.append(
            "Crowd prediction is currently "
            "unavailable for this destination."
        )

    else:

        lines.append(
            "Crowd prediction was not run "
            "because required inputs were "
            "unavailable."
        )

    lines.append("")

    lines.append(
        "No bookings have been made. "
        "Model outputs are predictions and "
        "should be treated as planning guidance."
    )

    return "\n".join(
        lines
    )


# ============================================================
# GEMINI FINAL PLAN
# MAXIMUM ONE GEMINI CALL
# ============================================================

def generate_ai_plan(
    user_request,
    requirements,
    destination_result,
    ml_results,
    budget_evaluation
):

    if client is None:

        raise RuntimeError(
            "Gemini API key is unavailable."
        )

    sources = destination_result.get(
        "sources",
        []
    )

    context = []

    for source in sources:

        context.append({
            "spot_name": source.get(
                "spot_name"
            ),

            "district": source.get(
                "district"
            ),

            "category": source.get(
                "category"
            ),

            "content": source.get(
                "content"
            )
        })

    prompt = f"""
You are Around You's AI Trip Advisor.

Create a concise and practical Telangana trip plan.

USER REQUEST:
{user_request}

TRIP REQUIREMENTS:
{json.dumps(requirements, indent=2, default=str)}

RETRIEVED DESTINATION KNOWLEDGE:
{json.dumps(context, indent=2, default=str)}

ML PREDICTIONS:
{json.dumps(ml_results, indent=2, default=str)}

BUDGET CHECK:
{json.dumps(budget_evaluation, indent=2, default=str)}

RULES:

1. Use only supplied destination knowledge
   for destination facts.

2. Do not invent destinations.

3. Do not invent prices.

4. Only describe ML predictions whose
   status is "success".

5. Never describe an ML result with status
   "error" as a prediction.

6. Clearly identify model outputs as predictions.

7. The user's transport_mode is the mode used
   for budget estimation.

8. The Transport ML output is an independent
   recommendation. Do not confuse the two.

9. If the budget status is within_budget,
   state the predicted cost and remaining amount.

10. If the budget status is over_budget,
    state the predicted cost and amount over budget.

11. If budget status is not_checked,
    say budget validation was unavailable.

12. Do not invent hotel names, routes,
    entry fees, opening hours or facilities.

13. Do not claim any booking has been made.

14. If duration is known, organize the
    destinations into a day-by-day itinerary.

15. Keep the answer readable and useful.

16. Do not expose Python or internal
    implementation details.
"""

    interaction = client.interactions.create(
        model=MODEL_NAME,
        input=prompt
    )

    if not interaction.output_text:

        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return (
        interaction.output_text
        .strip()
    )


# ============================================================
# MAIN AGENT
# ============================================================

def plan_trip(
    user_request,
    district=None,
    travel_date=None,
    budget_limit=None,
    num_travelers=None,
    accommodation_tier=None,
    transport_mode=None,
    route_distance_km=None,
    rainfall_mm=None,
    road_access_rating=None,
    festival=None
):

    tools_used = []

    # --------------------------------------------------------
    # 1. UNDERSTAND REQUEST
    # --------------------------------------------------------

    requirements = understand_request(
        user_request=user_request,
        district=district,
        travel_date=travel_date,
        budget_limit=budget_limit,
        num_travelers=num_travelers,
        accommodation_tier=accommodation_tier,
        transport_mode=transport_mode
    )

    tools_used.append(
        "understand_trip_request"
    )

    # --------------------------------------------------------
    # 2. RAG RETRIEVAL
    # --------------------------------------------------------

    destination_result = (
        run_destination_search(
            requirements
        )
    )

    tools_used.append(
        "faiss_destination_retrieval"
    )

    # --------------------------------------------------------
    # 3. ML TOOLS
    # --------------------------------------------------------

    ml_results = run_ml_tools(
        requirements=requirements,
        destination_result=destination_result,
        route_distance_km=route_distance_km,
        rainfall_mm=rainfall_mm,
        road_access_rating=road_access_rating,
        festival=festival
    )

    for name, result in (
        ml_results.items()
    ):

        if (
            result.get("status")
            == "success"
        ):

            tools_used.append(
                f"{name}_prediction"
            )

    # --------------------------------------------------------
    # 4. BUDGET CHECK
    # --------------------------------------------------------

    budget_evaluation = (
        evaluate_budget(
            ml_results=ml_results,
            budget_limit=requirements.get(
                "budget_limit"
            )
        )
    )

    tools_used.append(
        "budget_constraint_check"
    )

    # --------------------------------------------------------
    # 5. FINAL PLAN
    # --------------------------------------------------------

    generation_mode = "gemini"
    generation_error = None

    try:

        final_plan = generate_ai_plan(
            user_request=user_request,
            requirements=requirements,
            destination_result=destination_result,
            ml_results=ml_results,
            budget_evaluation=budget_evaluation
        )

        tools_used.append(
            "gemini_final_planner"
        )

    except Exception as error:

        generation_mode = "fallback"

        generation_error = str(
            error
        )

        final_plan = (
            generate_fallback_plan(
                requirements=requirements,
                destination_result=destination_result,
                ml_results=ml_results,
                budget_evaluation=budget_evaluation
            )
        )

        tools_used.append(
            "fallback_trip_planner"
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "request": user_request,

        "plan": final_plan,

        "tools_used": tools_used,

        "tool_results": {

            "requirements": requirements,

            "destination_search": (
                destination_result
            ),

            "ml_predictions": (
                ml_results
            ),

            "budget_evaluation": (
                budget_evaluation
            ),

            "generation": {
                "mode": generation_mode,

                "gemini_error": (
                    generation_error
                    if generation_error
                    else None
                )
            }
        }
    }