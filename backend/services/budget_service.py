import os
import sqlite3
from functools import lru_cache


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models",
    "budget"
)

DB_PATH = os.path.join(
    BASE_DIR,
    "data",
    "smart_tourism.db"
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "best_trip_cost_model.pkl"
)


# ---------------------------------------------------------
# OUTPUT COLUMNS
# ---------------------------------------------------------

COST_COLUMNS = [
    "travel_cost_est",
    "stay_cost_est",
    "food_cost_est",
    "entry_fees_est",
    "tolls_and_parking_est",
]


# ---------------------------------------------------------
# VALID INPUT VALUES
# ---------------------------------------------------------

VALID_ACCOMMODATION_TIERS = {
    "budget",
    "mid",
    "premium",
}

ACCOMMODATION_ALIASES = {
    "standard": "mid",
    "mid-range": "mid",
    "midrange": "mid",
    "luxury": "premium",
}

VALID_TRANSPORT_MODES = {
    "auto",
    "bike",
    "bus",
    "car",
    "train",
}


# ---------------------------------------------------------
# LAZY MODEL LOADER
# ---------------------------------------------------------

@lru_cache(maxsize=1)
def _get_budget_model():
    import joblib

    return joblib.load(MODEL_PATH)


# ---------------------------------------------------------
# LAZY PREPROCESSOR
# ---------------------------------------------------------

@lru_cache(maxsize=1)
def _get_budget_preprocessor():
    import pandas as pd

    from sklearn.compose import ColumnTransformer
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import (
        OrdinalEncoder,
        OneHotEncoder,
        StandardScaler,
    )

    conn = sqlite3.connect(DB_PATH)

    try:
        raw_df = pd.read_sql(
            "SELECT * FROM trip_budget_prediction;",
            conn,
        )
    finally:
        conn.close()

    df = raw_df.copy()
    df.columns = df.columns.str.lower()

    y = df[COST_COLUMNS]

    X = df.drop(
        columns=[
            "travel_cost_est",
            "stay_cost_est",
            "food_cost_est",
            "entry_fees_est",
        ]
    )

    X_train, _, _, _ = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "ordinal",
                OrdinalEncoder(),
                ["accommodation_tier"],
            ),
            (
                "nominal",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
                ["transport_mode", "season"],
            ),
            (
                "numeric",
                StandardScaler(),
                [
                    "duration_days",
                    "num_travelers",
                    "route_distance_km",
                ],
            ),
        ]
    )

    preprocessor.fit(X_train)

    return preprocessor


# ---------------------------------------------------------
# NORMALIZE USER INPUT
# ---------------------------------------------------------

def _normalize_budget_inputs(data: dict):
    normalized = dict(data)

    accommodation = str(
        normalized["accommodation_tier"]
    ).strip().lower()

    accommodation = ACCOMMODATION_ALIASES.get(
        accommodation,
        accommodation,
    )

    if accommodation not in VALID_ACCOMMODATION_TIERS:
        accommodation = "mid"

    transport = str(
        normalized["transport_mode"]
    ).strip().lower()

    if transport not in VALID_TRANSPORT_MODES:
        transport = "car"

    if accommodation == "mid":
        normalized["accommodation_tier"] = "Mid"
    else:
        normalized["accommodation_tier"] = (
            accommodation.capitalize()
        )

    normalized["transport_mode"] = transport

    return normalized


# ---------------------------------------------------------
# PREDICTION
# ---------------------------------------------------------

def predict_budget(data: dict):
    import pandas as pd

    data = _normalize_budget_inputs(data)

    budget_model = _get_budget_model()
    budget_preprocessor = _get_budget_preprocessor()

    new_trip = pd.DataFrame(
        [
            {
                "duration_days":
                    data["duration_days"],

                "num_travelers":
                    data["num_travelers"],

                "route_distance_km":
                    data["route_distance_km"],

                "transport_mode":
                    data["transport_mode"],

                "accommodation_tier":
                    data["accommodation_tier"],

                "season":
                    data["season"],
            }
        ]
    )

    X_final = budget_preprocessor.transform(
        new_trip
    )

    predicted = budget_model.predict(
        X_final
    )

    result = dict(
        zip(
            COST_COLUMNS,
            predicted[0].tolist(),
        )
    )

    result["predicted_total_cost"] = sum(
        result.values()
    )

    return result