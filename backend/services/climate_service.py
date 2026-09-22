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
    "climate"
)

DB_PATH = os.path.join(
    BASE_DIR,
    "data",
    "smart_tourism.db"
)


# ---------------------------------------------------------
# LAZY CLIMATE RESOURCE LOADER
# ---------------------------------------------------------

@lru_cache(maxsize=1)
def _get_climate_resources():
    import joblib
    import pandas as pd
    import torch
    from torch import nn

    # -----------------------------------------------------
    # MODEL CLASS
    # -----------------------------------------------------

    class ClimateLSTM(nn.Module):
        def __init__(
            self,
            input_size,
            hidden_size=24,
            num_layers=1,
            output_size=None,
            dropout=0.2,
        ):
            super().__init__()

            if output_size is None:
                output_size = input_size

            self.lstm = nn.LSTM(
                input_size,
                hidden_size,
                num_layers,
                batch_first=True,
            )

            self.dropout = nn.Dropout(dropout)

            self.fc = nn.Linear(
                hidden_size,
                output_size,
            )

        def forward(self, x):
            out, _ = self.lstm(x)

            out = self.dropout(
                out[:, -1, :]
            )

            out = self.fc(out)

            return out

    # -----------------------------------------------------
    # METADATA
    # -----------------------------------------------------

    metadata_path = os.path.join(
        MODEL_DIR,
        "best_climate_metadata.pkl",
    )

    climate_meta = joblib.load(
        metadata_path
    )

    seq_len = climate_meta["seq_len"]

    last_known_date = pd.Timestamp(
        climate_meta["last_known_date"]
    )

    target_cols = climate_meta[
        "target_cols"
    ]

    # -----------------------------------------------------
    # TRAINED MODEL
    # -----------------------------------------------------

    climate_model = ClimateLSTM(
        input_size=len(target_cols),
        hidden_size=24,
        num_layers=1,
        output_size=len(target_cols),
        dropout=0.2,
    )

    model_path = os.path.join(
        MODEL_DIR,
        "best_climate_lstm_model.pt",
    )

    state_dict = torch.load(
        model_path,
        map_location="cpu",
        weights_only=True,
    )

    climate_model.load_state_dict(
        state_dict
    )

    climate_model.eval()

    # -----------------------------------------------------
    # HISTORICAL CLIMATE DATA
    # -----------------------------------------------------

    conn = sqlite3.connect(DB_PATH)

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

    statewide = (
        raw.groupby("Date")[target_cols]
        .mean()
        .asfreq("D")
    )

    climate_diffed = (
        statewide.diff().dropna()
    )

    district_daily = raw.groupby(
        ["District", "Date"]
    )[target_cols].mean()

    climate_district_baseline = (
        district_daily.xs(
            last_known_date,
            level="Date",
        )
    )

    return (
        climate_model,
        seq_len,
        last_known_date,
        target_cols,
        climate_diffed,
        climate_district_baseline,
    )


# ---------------------------------------------------------
# PREDICTION
# ---------------------------------------------------------

def predict_climate(data: dict):
    import numpy as np
    import pandas as pd
    import torch

    (
        climate_model,
        seq_len,
        last_known_date,
        target_cols,
        climate_diffed,
        climate_district_baseline,
    ) = _get_climate_resources()

    forecast_date = pd.Timestamp(
        data["forecast_date"]
    )

    district = data["district"]

    days_ahead = (
        forecast_date -
        last_known_date
    ).days

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

    current_seq = torch.tensor(
        climate_diffed.values[
            -seq_len:
        ],
        dtype=torch.float32,
    ).unsqueeze(0)

    baseline = (
        climate_district_baseline.loc[
            district
        ]
    )

    future_diffs = []
    daily_forecast = []

    with torch.no_grad():

        for i in range(days_ahead):

            next_diff = climate_model(
                current_seq
            )

            future_diffs.append(
                next_diff
                .squeeze(0)
                .numpy()
            )

            current_seq = torch.cat(
                [
                    current_seq[
                        :, 1:, :
                    ],
                    next_diff.unsqueeze(1),
                ],
                dim=1,
            )

            cumulative_so_far = np.sum(
                future_diffs,
                axis=0,
            )

            day_values = (
                baseline +
                cumulative_so_far
            )

            day_date = (
                last_known_date +
                pd.Timedelta(
                    days=i + 1
                )
            )

            daily_forecast.append(
                {
                    "forecast_date":
                        day_date.strftime(
                            "%Y-%m-%d"
                        ),

                    **dict(
                        zip(
                            target_cols,
                            day_values.tolist(),
                        )
                    ),
                }
            )

    final_day = daily_forecast[-1]

    return {
        **{
            k: v
            for k, v in final_day.items()
            if k != "forecast_date"
        },

        "daily_forecast":
            daily_forecast,
    }