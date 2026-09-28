import json
import os
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from agent.tools import (
    search_destination_knowledge,
    search_selected_destinations,
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
        # Religious / spiritual
        "temple": "Temples",
        "temples": "Temples",
        "pilgrimage": "Pilgrimage",
        "religious": "Religious",

        # Heritage / history
        "kakatiya": "Kakatiya heritage",
        "fort": "Forts",
        "forts": "Forts",
        "museum": "Museums",
        "museums": "Museums",
        "history": "History",
        "historical": "History",
        "heritage": "History",
        "architecture": "Architecture",
        "architectural": "Architecture",
        "sculpture": "Sculptures",
        "sculptures": "Sculptures",

        # Nature
        "nature": "Nature",
        "natural": "Nature",
        "lake": "Lakes",
        "lakes": "Lakes",
        "waterfall": "Waterfalls",
        "waterfalls": "Waterfalls",
        "wildlife": "Wildlife",
        "sanctuary": "Wildlife",
        "forest": "Nature",
        "forests": "Nature",
        "park": "Parks",
        "parks": "Parks",

        # Leisure
        "leisure": "Leisure",
        "recreation": "Leisure",
        "zoo": "Leisure",
    }

    interests = []

    for keyword, label in known_interests.items():

        pattern = (
            r"\b"
            + re.escape(keyword)
            + r"\b"
        )

        if (
            re.search(
                pattern,
                text_lower
            )
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

# Some tourism areas span modern administrative district
# boundaries. Keep this mapping explicit so unrelated districts
# are never introduced accidentally.
TOURISM_REGION_DISTRICTS = {
    "warangal": [
        "Warangal",
        "Hanumakonda"
    ],
    "hanumakonda": [
        "Hanumakonda",
        "Warangal"
    ]
}


def get_allowed_destination_districts(
    requested_district
):

    if not requested_district:
        return []

    requested_clean = str(
        requested_district
    ).strip()

    associated = (
        TOURISM_REGION_DISTRICTS.get(
            requested_clean.lower()
        )
    )

    if associated:
        return associated

    return [
        requested_clean
    ]


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
            "religious",
            "pilgrimage"
        ],

        "Religious": [
            "religious",
            "temple",
            "pilgrimage",
            "spiritual"
        ],

        "Pilgrimage": [
            "pilgrimage",
            "temple",
            "religious"
        ],

        "Kakatiya heritage": [
            "kakatiya",
            "heritage",
            "historical"
        ],

        "Forts": [
            "fort",
            "heritage",
            "historical"
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
            "sculptural",
            "carving",
            "carvings"
        ],

        "Nature": [
            "nature",
            "natural",
            "lake",
            "waterfall",
            "wildlife",
            "sanctuary",
            "forest"
        ],

        "Lakes": [
            "lake",
            "reservoir",
            "nature"
        ],

        "Waterfalls": [
            "waterfall",
            "falls",
            "nature"
        ],

        "Wildlife": [
            "wildlife",
            "sanctuary",
            "zoo"
        ],

        "Parks": [
            "park",
            "garden",
            "recreation"
        ],

        "Leisure": [
            "leisure",
            "recreation",
            "park",
            "zoo"
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

def destination_matches_interest(
    source,
    interest
):

    return (
        destination_interest_score(
            source,
            [interest]
        )
        > 0
    )

def destination_unique_key(source):

    name = str(
        source.get(
            "spot_name",
            ""
        )
    ).strip().lower()

    district = str(
        source.get(
            "district",
            ""
        )
    ).strip().lower()

    # Normalize punctuation and separators
    name = re.sub(
        r"[^a-z0-9\s]",
        " ",
        name
    )

    # Remove location suffix that creates duplicate
    # naming variants such as:
    # "Mallikarjuna Swamy Temple - Inavolu"
    # "Inavolu Mallikarjuna Swamy Temple"
    words = name.split()

    normalized_words = sorted(
        set(words)
    )

    normalized_name = " ".join(
        normalized_words
    )

    return (
        normalized_name,
        district
    )
    
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

    duration_days = requirements.get(
        "duration_days"
    )

    allowed_districts = (
        get_allowed_destination_districts(
            requested_district
        )
    )

    allowed_lower = {
        str(district).strip().lower()
        for district in allowed_districts
    }

    requested_lower = (
        str(requested_district).strip().lower()
        if requested_district
        else None
    )

    # --------------------------------------------------------
    # GEOGRAPHIC FILTER
    # --------------------------------------------------------

    if allowed_lower:

        geographic_sources = [
            source
            for source in all_sources
            if str(
                source.get(
                    "district",
                    ""
                )
            ).strip().lower()
            in allowed_lower
        ]

    else:

        geographic_sources = list(
            all_sources
        )

    # --------------------------------------------------------
    # RANK SOURCES
    # --------------------------------------------------------

    ranked_sources = []

    for source in geographic_sources:

        interest_score = (
            destination_interest_score(
                source,
                interests
            )
        )

        source_district = str(
            source.get(
                "district",
                ""
            )
        ).strip().lower()

        exact_district_score = (
            1
            if (
                requested_lower
                and source_district
                == requested_lower
            )
            else 0
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
                exact_district_score,
                similarity,
                source
            )
        )

    # Interest relevance is the strongest signal.
    # Exact requested district is the second priority.
    # Semantic similarity is the third priority.

    ranked_sources.sort(
        key=lambda item: (
            item[0],
            item[1],
            item[2]
        ),
        reverse=True
    )

    selected = []
    selected_ids = set()

    # --------------------------------------------------------
    # GUARANTEE INTEREST COVERAGE
    # --------------------------------------------------------
    #
    # Example:
    #
    # Temples + Nature
    #
    # We try to include at least one matching destination
    # for each interest before filling the remaining slots.
    # --------------------------------------------------------

    if interests:

        for interest in interests:

            for (
                interest_score,
                exact_score,
                similarity,
                source
            ) in ranked_sources:

                if not destination_matches_interest(
                    source,
                    interest
                ):
                    continue
                
                unique_key = destination_unique_key(
                    source
                )

                if unique_key in selected_ids:
                    continue

                selected.append(
                    source
                )

                selected_ids.add(
                    unique_key
                )

                break

    # --------------------------------------------------------
    # FILL REMAINING DESTINATIONS
    # --------------------------------------------------------

    for (
        interest_score,
        exact_score,
        similarity,
        source
    ) in ranked_sources:

        if (
            interests
            and interest_score <= 0
        ):
            continue

        unique_key = destination_unique_key(
    source
)

        if unique_key in selected_ids:
            continue

        selected.append(
            source
        )

        selected_ids.add(
            unique_key
        )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------
    #
    # If none of the geographically valid destinations match
    # the requested interests, retain the geographically valid
    # destinations rather than returning nothing.
    # --------------------------------------------------------

    if not selected:

        selected = [
            item[3]
            for item in ranked_sources
        ]

    # --------------------------------------------------------
    # DURATION-AWARE RESULT LIMIT
    # --------------------------------------------------------

    try:

        days = max(
            1,
            int(duration_days)
        )

    except (
        TypeError,
        ValueError
    ):

        days = 2

    if days == 1:

        result_limit = 4

    elif days == 2:

        result_limit = 5

    else:

        result_limit = min(
            10,
            (days * 2) + 1
        )

    return {
        "query": destination_result.get(
            "query",
            ""
        ),

        "allowed_districts":
            allowed_districts,

        "sources":
            selected[
                :result_limit
            ]
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
            + ", ".join(
                interests
            )
            + "."
        )

    if not parts:

        parts.append(
            "Tourist destinations in Telangana."
        )

    query = " ".join(
        parts
    )

    # --------------------------------------------------------
    # DETERMINE APPROVED TOURISM REGION
    # --------------------------------------------------------

    allowed_districts = (
        get_allowed_destination_districts(
            destination
        )
    )

    # --------------------------------------------------------
    # DISTRICT-AWARE RAG SEARCH
    # --------------------------------------------------------
    #
    # rag_service.py now searches the complete FAISS index
    # before applying the allowed-district filter.
    #
    # This means Warangal can retrieve destinations from:
    #
    #   Warangal
    #   Hanumakonda
    #
    # without allowing unrelated Telangana districts.
    # --------------------------------------------------------

    raw_result = (
        search_destination_knowledge(
            query=query,
            top_k=30,
            districts=(
                allowed_districts
                if destination
                else None
            )
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

    source_districts = []

    for source in sources:

        source_district = str(
            source.get(
                "district",
                ""
            )
        ).strip()

        if (
            source_district
            and source_district
            not in source_districts
        ):

            source_districts.append(
                source_district
            )

    # If the user did not explicitly choose a district,
    # infer one only when every retrieved destination
    # belongs to the same district.
    if (
        not district
        and len(source_districts) == 1
    ):

        district = source_districts[0]

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
        "duration_days":
            duration_days,

        "num_travelers":
            num_travelers,

        "route_distance_km":
            route_distance_km,

        "accommodation_tier":
            accommodation_tier,

        "transport_mode":
            planned_transport,

        "season":
            season
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

                    "prediction":
                        prediction
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
        "distance_km":
            route_distance_km,

        "budget_limit":
            budget_limit,

        "num_people":
            num_travelers,

        "rainfall_mm":
            rainfall_mm,

        "road_access_rating":
            road_access_rating
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

                    "prediction":
                        prediction
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
                "retrieved_destination"
            ]
        }

    else:

        primary = sources[0]

        if not travel_date:

            results["crowd"] = {
                "status": "not_run",
                "missing_fields": [
                    "travel_date"
                ]
            }

        else:

            try:

                date = datetime.strptime(
                    travel_date,
                    "%Y-%m-%d"
                )

                prediction = (
                    run_crowd_prediction(
                        spot_name=primary.get(
                            "spot_name"
                        ),

                        district=primary.get(
                            "district"
                        ),

                        category=primary.get(
                            "category"
                        ),

                        year=date.year,

                        month=date.strftime(
                            "%B"
                        ),

                        season=season,

                        festival=(
                            festival
                            or "None"
                        )
                    )
                )

                if service_succeeded(
                    prediction
                ):

                    results["crowd"] = {
                        "status": "success",

                        "destination":
                            primary.get(
                                "spot_name"
                            ),

                        "prediction":
                            prediction
                    }

                else:

                    results["crowd"] = {
                        "status": "error",

                        "destination":
                            primary.get(
                                "spot_name"
                            ),

                        "message": (
                            service_error_message(
                                prediction
                            )
                        )
                    }

            except Exception as error:

                results["crowd"] = {
                    "status": "error",

                    "destination":
                        primary.get(
                            "spot_name"
                        ),

                    "message":
                        str(error)
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

Create a concise, practical and personalized Telangana trip plan.

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

1. Use only the supplied destination knowledge for destination facts.

2. Do not invent destinations, attractions, hotels, routes, opening hours,
   facilities, prices, entry fees or bookings.

3. Use the requested district and any explicitly supplied associated
   tourism-region destinations as the trip's geographic scope. Destinations
   from an associated district may be used when they appear in the supplied
   destination knowledge. Do not introduce any district or destination that
   is not present in the supplied knowledge.

4. Prefer destinations that match the traveler's stated interests.

5. If duration is known, create a day-by-day itinerary for exactly that
   number of days.

6. Use the available retrieved destinations across the itinerary. Avoid
   repeating the same destination on multiple days unless there are too few
   supplied destinations to create a sensible plan.

7. A day may contain more than one destination when practical. Do not assume
   that one destination must occupy an entire day.

8. Never invent extra destinations merely to fill unused days. If the
   supplied knowledge is insufficient for the requested duration, say that
   the available verified destination knowledge is limited and create a
   lighter itinerary using only the supplied places.

9. Only describe ML predictions whose status is "success".

10. Never describe an ML result with status "error" or "not_run" as a
    successful prediction.

11. Clearly identify model outputs as predictions or estimates rather than
    guaranteed real-world values.

12. The user's transport_mode is the mode used for budget estimation.
    The Transport ML output is an independent model recommendation. Do not
    replace the user's selected mode with the model recommendation and do
    not claim that the recommended mode is more comfortable, convenient,
    faster or better unless that information is explicitly supplied.

13. If the transport model recommends the same mode the user selected, you
    may state that the model recommendation aligns with the selected mode.
    If it differs, state the difference neutrally.

14. If budget status is within_budget, state the predicted total cost and
    predicted remaining amount.

15. If budget status is over_budget, state the predicted total cost and the
    predicted amount over budget. You may suggest changing broad planning
    inputs such as accommodation tier or trip duration, but do not invent
    specific hotel prices or savings.

16. If budget status is not_checked, say budget validation was unavailable.

17. For crowd predictions, describe the value as predicted visitor volume
    for the model's destination and period. Do not imply that this many
    people will physically be present at the exact moment the traveler
    arrives unless the supplied model output explicitly represents that.

18. Weather/climate outputs are model predictions. Do not convert rainfall
    probability or predicted rainfall into certainty that it will rain.

19. Do not claim any booking or reservation has been made.

20. The frontend displays budget, cost breakdown, transport, climate, crowd
    and recommended destinations separately. Do not repeat those sections
    in the generated plan. Focus the response on the personalized day-by-day
    itinerary and brief planning notes that are useful to the traveler.

21. Use this output structure:

    ## Trip Itinerary

    A single short introductory sentence.

    #### Day 1: Short descriptive title
    • **Destination:** destination name
    • **Plan:** concise description of what to do and why it matches the
    traveler's interests.
    • **Entry Fee:** include only when explicitly present in the supplied
    destination knowledge.

    Continue the same structure for every requested day.

    ### Planning Note
    Include this section only when useful, such as when verified destination
    knowledge is insufficient for the requested duration.

22. MARKDOWN FORMAT RULES:
    Use only:
    ## for the main itinerary heading
    ### for Planning Note
    #### for each day heading
    **text** for bold text
    • followed by a space for bullet points

    Do not use backslashes anywhere in the response.
    Do not escape Markdown characters.
    Do not use HTML or HTML entities.
    Do not use blockquotes.
    Do not use horizontal rules.
    Do not use italic Markdown.
    Do not use the tilde character for approximate values.
    Do not place Markdown formatting around punctuation.
    Use normal Unicode characters such as ₹ and ° directly.

23. Do not include separate Budget, Cost Breakdown, Climate, Crowd,
    Transport, Recommended Destinations, Trip Overview or Model Insights
    sections. Those values are already displayed by the frontend.

24. Do not expose raw JSON, Python, FAISS, internal tools or implementation
    details. Keep the itinerary concise and suitable for direct display in
    the Around You interface.
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
    selected_destinations=None,
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

    if selected_destinations:

        destination_result = (
        search_selected_destinations(
            selected_destinations
        )
    )

    else:

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

            "requirements":
                requirements,

            "destination_search":
                destination_result,

            "ml_predictions":
                ml_results,

            "budget_evaluation":
                budget_evaluation,

            "generation": {

                "mode":
                    generation_mode,

                "gemini_error": (
                    generation_error
                    if generation_error
                    else None
                )
            }
        }
    }