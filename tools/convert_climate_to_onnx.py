import os
import sys

import joblib
import torch
from torch import nn


# ============================================================
# PATHS
# ============================================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

PROJECT_DIR = os.path.dirname(
    SCRIPT_DIR
)

MODEL_DIR = os.path.join(
    PROJECT_DIR,
    "backend",
    "models",
    "climate"
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "best_climate_lstm_model.pt"
)

METADATA_PATH = os.path.join(
    MODEL_DIR,
    "best_climate_metadata.pkl"
)

ONNX_PATH = os.path.join(
    MODEL_DIR,
    "best_climate_lstm_model.onnx"
)


# ============================================================
# MODEL CLASS
# Must match the original trained architecture exactly.
# ============================================================

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

        self.dropout = nn.Dropout(
            dropout
        )

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


# ============================================================
# CONVERSION
# ============================================================

def main():

    print("=" * 60)
    print("Around You - Climate PyTorch -> ONNX")
    print("=" * 60)

    # --------------------------------------------------------
    # Verify files
    # --------------------------------------------------------

    if not os.path.exists(MODEL_PATH):
        print(
            f"\nERROR: Model not found:\n{MODEL_PATH}"
        )
        sys.exit(1)

    if not os.path.exists(METADATA_PATH):
        print(
            f"\nERROR: Metadata not found:\n{METADATA_PATH}"
        )
        sys.exit(1)

    print("\nLoading climate metadata...")

    climate_meta = joblib.load(
        METADATA_PATH
    )

    seq_len = int(
        climate_meta["seq_len"]
    )

    target_cols = climate_meta[
        "target_cols"
    ]

    input_size = len(
        target_cols
    )

    print(
        f"Sequence length : {seq_len}"
    )

    print(
        f"Input features  : {input_size}"
    )

    print(
        f"Target columns  : {target_cols}"
    )

    # --------------------------------------------------------
    # Rebuild model architecture
    # --------------------------------------------------------

    print("\nRebuilding LSTM architecture...")

    model = ClimateLSTM(
        input_size=input_size,
        hidden_size=24,
        num_layers=1,
        output_size=input_size,
        dropout=0.2,
    )

    # --------------------------------------------------------
    # Load trained weights
    # --------------------------------------------------------

    print("Loading trained PyTorch weights...")

    state_dict = torch.load(
        MODEL_PATH,
        map_location="cpu",
        weights_only=True,
    )

    model.load_state_dict(
        state_dict
    )

    model.eval()

    # --------------------------------------------------------
    # Dummy input
    #
    # Shape:
    # batch_size x sequence_length x input_features
    # --------------------------------------------------------

    dummy_input = torch.randn(
        1,
        seq_len,
        input_size,
        dtype=torch.float32,
    )

    # --------------------------------------------------------
    # Test original model
    # --------------------------------------------------------

    print(
        "Testing PyTorch model before export..."
    )

    with torch.no_grad():
        torch_output = model(
            dummy_input
        )

    print(
        "PyTorch output shape:",
        tuple(torch_output.shape)
    )

    # --------------------------------------------------------
    # Export ONNX
    # --------------------------------------------------------

    print("\nExporting ONNX model...")

    torch.onnx.export(
        model,
        dummy_input,
        ONNX_PATH,

        input_names=[
            "input"
        ],

        output_names=[
            "output"
        ],

        dynamic_axes={
            "input": {
                0: "batch_size"
            },

            "output": {
                0: "batch_size"
            },
        },

        opset_version=17,

        do_constant_folding=True,
    )

    # --------------------------------------------------------
    # Verify file
    # --------------------------------------------------------

    if not os.path.exists(
        ONNX_PATH
    ):
        print(
            "\nERROR: ONNX export failed."
        )
        sys.exit(1)

    file_size_mb = (
        os.path.getsize(
            ONNX_PATH
        )
        / (1024 * 1024)
    )

    print("\n" + "=" * 60)

    print(
        "ONNX CONVERSION SUCCESSFUL"
    )

    print("=" * 60)

    print(
        f"\nSaved to:\n{ONNX_PATH}"
    )

    print(
        f"\nONNX size: {file_size_mb:.2f} MB"
    )

    print(
        "\nDo NOT delete the original .pt model."
    )


if __name__ == "__main__":
    main()