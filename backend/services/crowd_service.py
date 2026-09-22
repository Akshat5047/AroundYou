import os

import joblib
import pandas as pd


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models",
    "crowd"
)


# ---------------------------------------------------------
# LOAD MODEL + PREPROCESSING ARTIFACTS
# ---------------------------------------------------------

crowd_model = joblib.load(
    os.path.join(
        MODEL_DIR,
        "crowd_model.pkl"
    )
)

crowd_preprocessor = joblib.load(
    os.path.join(
        MODEL_DIR,
        "preprocessor.pkl"
    )
)

crowd_spot_mean_map = joblib.load(
    os.path.join(
        MODEL_DIR,
        "spot_mean_map.pkl"
    )
)

crowd_district_mean_map = joblib.load(
    os.path.join(
        MODEL_DIR,
        "district_mean_map.pkl"
    )
)

crowd_month_mean_map = joblib.load(
    os.path.join(
        MODEL_DIR,
        "month_mean_map.pkl"
    )
)

crowd_season_mean_map = joblib.load(
    os.path.join(
        MODEL_DIR,
        "season_mean_map.pkl"
    )
)

crowd_global_mean = joblib.load(
    os.path.join(
        MODEL_DIR,
        "global_visitor_mean.pkl"
    )
)


# ---------------------------------------------------------
# PREDICTION
# ---------------------------------------------------------

def predict_crowd(data: dict):

    new_row = pd.DataFrame([data])

    # -----------------------------------------------------
    # MEAN ENCODING
    # -----------------------------------------------------

    new_row["spot_name_mean"] = (
        new_row["spot_name"]
        .map(crowd_spot_mean_map)
        .fillna(crowd_global_mean)
    )

    new_row["district_mean"] = (
        new_row["district"]
        .map(crowd_district_mean_map)
        .fillna(crowd_global_mean)
    )

    new_row["month_mean"] = (
        new_row["month"]
        .map(crowd_month_mean_map)
        .fillna(crowd_global_mean)
    )

    new_row["season_mean"] = (
        new_row["season"]
        .map(crowd_season_mean_map)
        .fillna(crowd_global_mean)
    )

    # -----------------------------------------------------
    # PREPROCESS
    # -----------------------------------------------------

    X_final = crowd_preprocessor.transform(
        new_row
    )

    # -----------------------------------------------------
    # PREDICT
    # -----------------------------------------------------

    predicted_visitors = crowd_model.predict(
        X_final
    )

    visitors = float(
        predicted_visitors[0]
    )

    # Visitor count should never be negative
    visitors = max(0.0, visitors)

    return {
        "predicted_total_visitors":
            visitors
    }