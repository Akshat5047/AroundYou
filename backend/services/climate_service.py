import os
import sqlite3
from functools import lru_cache


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models",
    "climate"
)

DB_PATH = os.path.join(
    BASE_DIR,
    "data",
    "smart_tourism.db"
)

ONNX_MODEL_PATH = os.path.join(
    MODEL_DIR,
    "best_climate_lstm_model.onnx"
)

METADATA_PATH = os.path.join(
    MODEL_DIR,
    "best_climate_metadata.pkl"
)


# ============================================================
# LAZY CLIMATE RESOURCE LOADER
# ============================================================

@lru_cache(maxsize=1)
def _get_climate_resources():

    import joblib
    import pandas as pd
    import onnxruntime as ort

    # --------------------------------------------------------
    # LOAD METADATA
    # --------------------------------------------------------

    climate_meta = joblib.load(
        METADATA_PATH
    )

    seq_len = int(
        climate_meta["seq_len"]
    )

    last_known_date = pd.Timestamp(
        climate_meta["last_known_date"]
    )

    target_cols = climate_meta[
        "target_cols"
    ]

    # --------------------------------------------------------
    # LOAD ONNX MODEL
    # --------------------------------------------------------

    session_options = (
        ort.SessionOptions()
    )

    # Keep memory/thread usage conservative for Render Free.
    session_options.intra_op_num_threads = 1
    session_options.inter_op_num_threads = 1

    climate_session = (
        ort.InferenceSession(
            ONNX_MODEL_PATH,
            sess_options=session_options,
            providers=[
                "CPUExecutionProvider"
            ],
        )
    )

    input_name = (
        climate_session
        .get_inputs()[0]
        .name
    )

    output_name = (
        climate_session
        .get_outputs()[0]
        .name
    )

    # --------------------------------------------------------
    # LOAD HISTORICAL CLIMATE DATA
    # --------------------------------------------------------

    conn = sqlite3.connect(
        DB_PATH
    )

    try:

        raw = pd.read_sql(
            "SELECT * FROM climate_dataset",
            conn,
        )

    finally:

        conn.close()

    raw["Date"] = pd.to_datetime(
        raw["Date"]
    )

    # --------------------------------------------------------
    # RAINFALL PERCENT
    # --------------------------------------------------------

    raw["Is_Rain_Day"] = (
        raw["Rainfall_mm"] >= 1.0
    ).astype(int)

    raw["Rainfall_Percent"] = (
        raw.groupby(
            "District"
        )["Is_Rain_Day"]
        .transform(
            lambda s:
            s.rolling(
                7,
                min_periods=1,
            ).mean() * 100
        )
    )

    # --------------------------------------------------------
    # STATEWIDE DAILY VALUES
    # --------------------------------------------------------

    statewide = (
        raw.groupby(
            "Date"
        )[target_cols]
        .mean()
        .asfreq("D")
    )

    climate_diffed = (
        statewide
        .diff()
        .dropna()
    )

    # --------------------------------------------------------
    # DISTRICT BASELINE
    # --------------------------------------------------------

    district_daily = (
        raw.groupby(
            [
                "District",
                "Date",
            ]
        )[target_cols]
        .mean()
    )

    climate_district_baseline = (
        district_daily.xs(
            last_known_date,
            level="Date",
        )
    )

    return {
        "session":
            climate_session,

        "input_name":
            input_name,

        "output_name":
            output_name,

        "seq_len":
            seq_len,

        "last_known_date":
            last_known_date,

        "target_cols":
            target_cols,

        "climate_diffed":
            climate_diffed,

        "district_baseline":
            climate_district_baseline,
    }


# ============================================================
# PREDICTION
# ============================================================

def predict_climate(data: dict):

    import numpy as np
    import pandas as pd

    resources = (
        _get_climate_resources()
    )

    climate_session = resources[
        "session"
    ]

    input_name = resources[
        "input_name"
    ]

    output_name = resources[
        "output_name"
    ]

    seq_len = resources[
        "seq_len"
    ]

    last_known_date = resources[
        "last_known_date"
    ]

    target_cols = resources[
        "target_cols"
    ]

    climate_diffed = resources[
        "climate_diffed"
    ]

    climate_district_baseline = (
        resources[
            "district_baseline"
        ]
    )

    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------

    forecast_date = pd.Timestamp(
        data["forecast_date"]
    )

    district = data[
        "district"
    ]

    days_ahead = (
        forecast_date -
        last_known_date
    ).days

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if days_ahead < 1:

        return {
            "error":
                f"forecast_date must be strictly after "
                f"{last_known_date.date()}"
        }

    if district not in (
        climate_district_baseline.index
    ):

        return {
            "error":
                f"'{district}' not found in climate data"
        }

    # --------------------------------------------------------
    # INITIAL SEQUENCE
    #
    # Shape:
    # (1, sequence_length, features)
    # --------------------------------------------------------

    current_seq = (
        climate_diffed
        .values[-seq_len:]
        .astype(np.float32)
    )

    current_seq = np.expand_dims(
        current_seq,
        axis=0,
    )

    baseline = (
        climate_district_baseline
        .loc[district]
    )

    baseline_values = (
        baseline
        .values
        .astype(np.float32)
    )

    # --------------------------------------------------------
    # RECURSIVE FORECAST
    # --------------------------------------------------------

    cumulative_diff = np.zeros(
        len(target_cols),
        dtype=np.float32,
    )

    daily_forecast = []

    for i in range(
        days_ahead
    ):

        # ----------------------------------------------
        # ONNX inference
        # ----------------------------------------------

        next_diff = (
            climate_session.run(
                [output_name],
                {
                    input_name:
                        current_seq
                },
            )[0]
        )

        # Expected output:
        # (1, number_of_features)

        next_diff = (
            next_diff[0]
            .astype(np.float32)
        )

        # ----------------------------------------------
        # Update sequence
        # ----------------------------------------------

        next_step = np.expand_dims(
            next_diff,
            axis=(0, 1),
        )

        current_seq = np.concatenate(
            [
                current_seq[
                    :, 1:, :
                ],

                next_step,
            ],
            axis=1,
        )

        # ----------------------------------------------
        # Reconstruct actual climate values
        # ----------------------------------------------

        cumulative_diff += (
            next_diff
        )

        day_values = (
            baseline_values +
            cumulative_diff
        )

        day_date = (
            last_known_date +
            pd.Timedelta(
                days=i + 1
            )
        )

        row = {
            "forecast_date":
                day_date.strftime(
                    "%Y-%m-%d"
                )
        }

        for column, value in zip(
            target_cols,
            day_values,
        ):

            row[str(column)] = float(
                value
            )

        daily_forecast.append(
            row
        )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    final_day = (
        daily_forecast[-1]
    )

    return {
        **{
            key: value
            for key, value
            in final_day.items()
            if key != "forecast_date"
        },

        "daily_forecast":
            daily_forecast,
    }