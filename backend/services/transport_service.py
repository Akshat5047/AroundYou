import os
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
    "transport"
)


# ---------------------------------------------------------
# FEATURE ORDER
# ---------------------------------------------------------

TRANSPORT_FEATURE_COLS = [
    "distance_km",
    "budget_limit",
    "num_people",
    "rainfall_mm",
    "road_access_rating",
]


# ---------------------------------------------------------
# LAZY LOAD ARTIFACTS
# ---------------------------------------------------------

@lru_cache(maxsize=1)
def _get_transport_resources():
    import joblib

    transport_model = joblib.load(
        os.path.join(
            MODEL_DIR,
            "transport_mode_model.pkl"
        )
    )

    transport_scaler = joblib.load(
        os.path.join(
            MODEL_DIR,
            "transport_mode_scaler.pkl"
        )
    )

    transport_label_encoder = joblib.load(
        os.path.join(
            MODEL_DIR,
            "transport_mode_label_encoder.pkl"
        )
    )

    return (
        transport_model,
        transport_scaler,
        transport_label_encoder,
    )


# ---------------------------------------------------------
# PREDICTION
# ---------------------------------------------------------

def predict_transport(data: dict):
    import pandas as pd

    (
        transport_model,
        transport_scaler,
        transport_label_encoder,
    ) = _get_transport_resources()

    new_row = pd.DataFrame([
        {
            "distance_km":
                data["distance_km"],

            "budget_limit":
                data["budget_limit"],

            "num_people":
                data["num_people"],

            "rainfall_mm":
                data["rainfall_mm"],

            "road_access_rating":
                data["road_access_rating"],
        }
    ])[TRANSPORT_FEATURE_COLS]

    # Scale input
    X_scaled = transport_scaler.transform(
        new_row
    )

    # Predict encoded class
    predicted_class = (
        transport_model.predict(
            X_scaled
        )[0]
    )

    # Convert class back to transport name
    predicted_mode = (
        transport_label_encoder
        .inverse_transform(
            [predicted_class]
        )[0]
    )

    # Prediction probabilities
    probabilities = (
        transport_model
        .predict_proba(
            X_scaled
        )[0]
    )

    probability_by_mode = dict(
        zip(
            transport_label_encoder.classes_,
            probabilities.tolist()
        )
    )

    return {
        "recommended_transport_mode":
            str(predicted_mode),

        "confidence":
            float(
                max(probabilities)
            ),

        "probabilities":
            probability_by_mode,
    }