from pathlib import Path
import shutil
import sys

import torch
from transformers import AutoModel, AutoTokenizer


# ============================================================
# PATHS / SETTINGS
# ============================================================

PROJECT_DIR = Path(
    __file__
).resolve().parent.parent

OUTPUT_DIR = (
    PROJECT_DIR
    / "backend"
    / "models"
    / "rag_embedding"
)

ONNX_PATH = (
    OUTPUT_DIR
    / "model.onnx"
)

MODEL_NAME = (
    "sentence-transformers/"
    "all-MiniLM-L6-v2"
)


# ============================================================
# ONNX WRAPPER
# ============================================================

class MiniLMForONNX(torch.nn.Module):
    """
    Wraps the Hugging Face transformer.

    SentenceTransformer performs additional mean pooling and
    L2 normalization outside the transformer. We intentionally
    export the transformer output here and reproduce pooling
    later in the lightweight inference service.
    """

    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(
        self,
        input_ids,
        attention_mask,
        token_type_ids,
    ):
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            return_dict=False,
        )

        # Last hidden state:
        # [batch, sequence_length, hidden_size]
        return outputs[0]


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("Around You - RAG MiniLM ONNX Export")
    print("=" * 65)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        f"\nModel: {MODEL_NAME}"
    )

    print(
        f"Output directory:\n{OUTPUT_DIR}"
    )

    # --------------------------------------------------------
    # LOAD TOKENIZER
    # --------------------------------------------------------

    print(
        "\nLoading tokenizer..."
    )

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME
    )

    # --------------------------------------------------------
    # LOAD TRANSFORMER
    # --------------------------------------------------------

    print(
        "Loading transformer model..."
    )

    transformer = AutoModel.from_pretrained(
        MODEL_NAME
    )

    transformer.eval()

    wrapper = MiniLMForONNX(
        transformer
    )

    wrapper.eval()

    # --------------------------------------------------------
    # SAVE TOKENIZER
    # --------------------------------------------------------

    print(
        "Saving tokenizer..."
    )

    tokenizer.save_pretrained(
        OUTPUT_DIR
    )

    # Save model config too.
    transformer.config.save_pretrained(
        OUTPUT_DIR
    )

    # --------------------------------------------------------
    # CREATE TEST INPUT
    # --------------------------------------------------------

    test_text = (
        "What can I see at Golconda Fort?"
    )

    encoded = tokenizer(
        test_text,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=256,
    )

    input_ids = encoded[
        "input_ids"
    ]

    attention_mask = encoded[
        "attention_mask"
    ]

    # MiniLM normally supports token_type_ids.
    # Create zeros if tokenizer does not return them.
    if "token_type_ids" in encoded:

        token_type_ids = encoded[
            "token_type_ids"
        ]

    else:

        token_type_ids = torch.zeros_like(
            input_ids
        )

    print(
        "\nInput shape:",
        tuple(input_ids.shape)
    )

    # --------------------------------------------------------
    # VERIFY PYTORCH OUTPUT
    # --------------------------------------------------------

    print(
        "Testing transformer before export..."
    )

    with torch.no_grad():

        output = wrapper(
            input_ids,
            attention_mask,
            token_type_ids,
        )

    print(
        "Transformer output shape:",
        tuple(output.shape)
    )

    if output.shape[-1] != 384:

        print(
            "\nERROR: Expected hidden dimension 384, "
            f"but received {output.shape[-1]}."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # REMOVE PREVIOUS ONNX MODEL
    # --------------------------------------------------------

    if ONNX_PATH.exists():

        print(
            "\nRemoving previous ONNX export..."
        )

        ONNX_PATH.unlink()

    # --------------------------------------------------------
    # EXPORT
    # --------------------------------------------------------

    print(
        "\nExporting transformer to ONNX..."
    )

    torch.onnx.export(
        wrapper,

        (
            input_ids,
            attention_mask,
            token_type_ids,
        ),

        str(ONNX_PATH),

        input_names=[
            "input_ids",
            "attention_mask",
            "token_type_ids",
        ],

        output_names=[
            "last_hidden_state",
        ],

        dynamic_axes={
            "input_ids": {
                0: "batch_size",
                1: "sequence_length",
            },

            "attention_mask": {
                0: "batch_size",
                1: "sequence_length",
            },

            "token_type_ids": {
                0: "batch_size",
                1: "sequence_length",
            },

            "last_hidden_state": {
                0: "batch_size",
                1: "sequence_length",
            },
        },

        opset_version=17,

        do_constant_folding=True,
    )

    # --------------------------------------------------------
    # CHECK RESULT
    # --------------------------------------------------------

    if not ONNX_PATH.exists():

        print(
            "\nERROR: ONNX model was not created."
        )

        sys.exit(1)

    size_mb = (
        ONNX_PATH.stat().st_size
        / 1024
        / 1024
    )

    print(
        "\n" + "=" * 65
    )

    print(
        "EXPORT SUCCESSFUL"
    )

    print(
        "=" * 65
    )

    print(
        f"\nONNX model:\n{ONNX_PATH}"
    )

    print(
        f"\nModel size: {size_mb:.2f} MB"
    )

    print(
        "\nTokenizer/config files:"
    )

    for path in sorted(
        OUTPUT_DIR.iterdir()
    ):

        print(
            f"  - {path.name}"
        )

    print(
        "\nDo not delete your existing FAISS index."
    )

    print(
        "Do not modify the existing metadata.csv."
    )


if __name__ == "__main__":
    main()