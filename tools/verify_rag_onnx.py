from pathlib import Path

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer


# ============================================================
# PATHS
# ============================================================

PROJECT_DIR = Path(
    __file__
).resolve().parent.parent

MODEL_DIR = (
    PROJECT_DIR
    / "backend"
    / "models"
    / "rag_embedding"
)

ONNX_PATH = (
    MODEL_DIR
    / "model.onnx"
)

MODEL_NAME = (
    "sentence-transformers/"
    "all-MiniLM-L6-v2"
)


# ============================================================
# MEAN POOLING
# ============================================================

def mean_pooling(
    token_embeddings,
    attention_mask,
):
    mask = np.expand_dims(
        attention_mask,
        axis=-1,
    ).astype(np.float32)

    summed = np.sum(
        token_embeddings * mask,
        axis=1,
    )

    counts = np.clip(
        np.sum(
            mask,
            axis=1,
        ),
        a_min=1e-9,
        a_max=None,
    )

    return summed / counts


# ============================================================
# L2 NORMALIZATION
# ============================================================

def normalize_embeddings(
    embeddings,
):
    norms = np.linalg.norm(
        embeddings,
        axis=1,
        keepdims=True,
    )

    norms = np.clip(
        norms,
        a_min=1e-12,
        a_max=None,
    )

    return embeddings / norms


# ============================================================
# ONNX EMBEDDING
# ============================================================

def get_onnx_embedding(
    text,
    tokenizer,
    session,
):
    encoded = tokenizer(
        text,
        return_tensors="np",
        padding=True,
        truncation=True,
        max_length=256,
    )

    input_ids = (
        encoded["input_ids"]
        .astype(np.int64)
    )

    attention_mask = (
        encoded["attention_mask"]
        .astype(np.int64)
    )

    if "token_type_ids" in encoded:

        token_type_ids = (
            encoded["token_type_ids"]
            .astype(np.int64)
        )

    else:

        token_type_ids = (
            np.zeros_like(
                input_ids,
                dtype=np.int64,
            )
        )

    outputs = session.run(
        ["last_hidden_state"],
        {
            "input_ids":
                input_ids,

            "attention_mask":
                attention_mask,

            "token_type_ids":
                token_type_ids,
        },
    )

    token_embeddings = outputs[0]

    embeddings = mean_pooling(
        token_embeddings,
        attention_mask,
    )

    embeddings = normalize_embeddings(
        embeddings
    )

    return embeddings.astype(
        np.float32
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("Around You - RAG Embedding Verification")
    print("=" * 65)

    # --------------------------------------------------------
    # ORIGINAL SENTENCE TRANSFORMER
    # --------------------------------------------------------

    print(
        "\nLoading original SentenceTransformer..."
    )

    original_model = (
        SentenceTransformer(
            MODEL_NAME
        )
    )

    # --------------------------------------------------------
    # ONNX TOKENIZER
    # --------------------------------------------------------

    print(
        "Loading local tokenizer..."
    )

    tokenizer = (
        AutoTokenizer.from_pretrained(
            MODEL_DIR,
            local_files_only=True,
        )
    )

    # --------------------------------------------------------
    # ONNX SESSION
    # --------------------------------------------------------

    print(
        "Loading ONNX model..."
    )

    options = (
        ort.SessionOptions()
    )

    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1

    session = (
        ort.InferenceSession(
            str(ONNX_PATH),
            sess_options=options,
            providers=[
                "CPUExecutionProvider"
            ],
        )
    )

    # --------------------------------------------------------
    # TEST QUERIES
    # --------------------------------------------------------

    test_queries = [
        "What can I see at Golconda Fort?",
        "Tell me about Charminar.",
        "What is special about Ramappa Temple?",
        "Places to visit in Warangal",
        "Is Hussain Sagar worth visiting?",
    ]

    similarities = []

    print(
        "\nComparing embeddings...\n"
    )

    for query in test_queries:

        original_embedding = (
            original_model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True,
            )
            .astype(np.float32)
        )

        onnx_embedding = (
            get_onnx_embedding(
                query,
                tokenizer,
                session,
            )
        )

        similarity = float(
            np.sum(
                original_embedding[0]
                * onnx_embedding[0]
            )
        )

        max_difference = float(
            np.max(
                np.abs(
                    original_embedding
                    - onnx_embedding
                )
            )
        )

        similarities.append(
            similarity
        )

        print(
            f"Query: {query}"
        )

        print(
            f"Cosine similarity: "
            f"{similarity:.8f}"
        )

        print(
            f"Maximum difference: "
            f"{max_difference:.8f}"
        )

        print("-" * 65)

    average_similarity = float(
        np.mean(similarities)
    )

    print(
        "\nAverage cosine similarity:",
        f"{average_similarity:.8f}"
    )

    print()

    if average_similarity >= 0.999:

        print(
            "RESULT: PASS"
        )

        print(
            "The ONNX embeddings match the "
            "SentenceTransformer embedding space."
        )

    elif average_similarity >= 0.99:

        print(
            "RESULT: ACCEPTABLE"
        )

        print(
            "The embeddings are extremely close, "
            "but not numerically identical."
        )

    else:

        print(
            "RESULT: FAIL"
        )

        print(
            "Do NOT replace the RAG embedding "
            "implementation yet."
        )


if __name__ == "__main__":
    main()