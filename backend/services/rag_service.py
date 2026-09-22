from pathlib import Path
from functools import lru_cache
import os


# ============================================================
# PATHS
# ============================================================

BACKEND_DIR = Path(
    __file__
).resolve().parent.parent

PROJECT_DIR = BACKEND_DIR.parent

RAG_DIR = (
    PROJECT_DIR
    / "ai"
    / "rag"
)

INDEX_PATH = (
    RAG_DIR
    / "vector_store"
    / "destination.index"
)

METADATA_PATH = (
    RAG_DIR
    / "vector_store"
    / "metadata.csv"
)

EMBEDDING_MODEL_DIR = (
    BACKEND_DIR
    / "models"
    / "rag_embedding"
)

ONNX_MODEL_PATH = (
    EMBEDDING_MODEL_DIR
    / "model.onnx"
)


# ============================================================
# LAZY GEMINI CLIENT
# ============================================================

@lru_cache(maxsize=1)
def _get_gemini_client():

    from dotenv import load_dotenv
    from google import genai

    load_dotenv(
        PROJECT_DIR / ".env"
    )

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:

        raise ValueError(
            "GEMINI_API_KEY not found"
        )

    return genai.Client(
        api_key=api_key
    )


# ============================================================
# LAZY RAG RESOURCES
# ============================================================

@lru_cache(maxsize=1)
def _get_rag_resources():

    import faiss
    import pandas as pd
    import onnxruntime as ort

    from transformers import (
        AutoTokenizer
    )

    # --------------------------------------------------------
    # FAISS
    # --------------------------------------------------------

    index = faiss.read_index(
        str(INDEX_PATH)
    )

    # --------------------------------------------------------
    # METADATA
    # --------------------------------------------------------

    metadata = pd.read_csv(
        METADATA_PATH
    )

    # --------------------------------------------------------
    # LOCAL TOKENIZER
    #
    # No Hugging Face download occurs on Render.
    # --------------------------------------------------------

    tokenizer = (
        AutoTokenizer.from_pretrained(
            EMBEDDING_MODEL_DIR,
            local_files_only=True,
        )
    )

    # --------------------------------------------------------
    # ONNX SESSION
    # --------------------------------------------------------

    session_options = (
        ort.SessionOptions()
    )

    # Conservative settings for Render Free.
    session_options.intra_op_num_threads = 1
    session_options.inter_op_num_threads = 1

    embedding_session = (
        ort.InferenceSession(
            str(ONNX_MODEL_PATH),
            sess_options=session_options,
            providers=[
                "CPUExecutionProvider"
            ],
        )
    )

    return (
        index,
        metadata,
        tokenizer,
        embedding_session,
    )


# ============================================================
# MEAN POOLING
# ============================================================

def _mean_pooling(
    token_embeddings,
    attention_mask,
):

    import numpy as np

    mask = np.expand_dims(
        attention_mask,
        axis=-1,
    ).astype(
        np.float32
    )

    summed = np.sum(
        token_embeddings * mask,
        axis=1,
    )

    counts = np.sum(
        mask,
        axis=1,
    )

    counts = np.clip(
        counts,
        a_min=1e-9,
        a_max=None,
    )

    return (
        summed / counts
    )


# ============================================================
# L2 NORMALIZATION
# ============================================================

def _normalize_embeddings(
    embeddings,
):

    import numpy as np

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

    return (
        embeddings / norms
    )


# ============================================================
# LIGHTWEIGHT ONNX EMBEDDING
# ============================================================

def create_query_embedding(
    text: str,
):

    import numpy as np

    (
        _,
        _,
        tokenizer,
        embedding_session,
    ) = _get_rag_resources()

    encoded = tokenizer(
        text,
        return_tensors="np",
        padding=True,
        truncation=True,
        max_length=256,
    )

    input_ids = (
        encoded[
            "input_ids"
        ]
        .astype(np.int64)
    )

    attention_mask = (
        encoded[
            "attention_mask"
        ]
        .astype(np.int64)
    )

    if "token_type_ids" in encoded:

        token_type_ids = (
            encoded[
                "token_type_ids"
            ]
            .astype(np.int64)
        )

    else:

        token_type_ids = (
            np.zeros_like(
                input_ids,
                dtype=np.int64,
            )
        )

    token_embeddings = (
        embedding_session.run(
            [
                "last_hidden_state"
            ],
            {
                "input_ids":
                    input_ids,

                "attention_mask":
                    attention_mask,

                "token_type_ids":
                    token_type_ids,
            },
        )[0]
    )

    embeddings = _mean_pooling(
        token_embeddings,
        attention_mask,
    )

    embeddings = (
        _normalize_embeddings(
            embeddings
        )
    )

    return embeddings.astype(
        np.float32
    )


# ============================================================
# RETRIEVAL
# ============================================================

def retrieve_documents(
    question: str,
    top_k: int = 3,
):

    (
        index,
        metadata,
        _,
        _,
    ) = _get_rag_resources()

    query_embedding = (
        create_query_embedding(
            question
        )
    )

    search_count = min(
        top_k,
        index.ntotal,
    )

    scores, indices = (
        index.search(
            query_embedding,
            search_count,
        )
    )

    results = []

    for score, idx in zip(
        scores[0],
        indices[0],
    ):

        if idx == -1:
            continue

        row = metadata.iloc[
            idx
        ]

        results.append(
            {
                "document_id":
                    str(
                        row[
                            "document_id"
                        ]
                    ),

                "spot_name":
                    str(
                        row[
                            "spot_name"
                        ]
                    ),

                "district":
                    str(
                        row[
                            "district"
                        ]
                    ),

                "category":
                    str(
                        row[
                            "category"
                        ]
                    ),

                "knowledge_type":
                    str(
                        row[
                            "knowledge_type"
                        ]
                    ),

                "content":
                    str(
                        row[
                            "content"
                        ]
                    ),

                "similarity":
                    float(
                        score
                    ),
            }
        )

    return results


# ============================================================
# CONTEXT
# ============================================================

def build_context(
    results
):

    sections = []

    for number, result in enumerate(
        results,
        start=1,
    ):

        sections.append(
            f"""
Source {number}
Destination: {result['spot_name']}
District: {result['district']}
Category: {result['category']}
Information: {result['content']}
""".strip()
        )

    return "\n\n".join(
        sections
    )


# ============================================================
# RAG
# ============================================================

def answer_question(
    question: str,
    top_k: int = 3,
):

    results = retrieve_documents(
        question=question,
        top_k=top_k,
    )

    if (
        not results
        or results[0][
            "similarity"
        ] < 0.25
    ):

        return {
            "question":
                question,

            "answer": (
                "I don't have enough relevant "
                "information in the Around You "
                "knowledge base to answer that "
                "reliably."
            ),

            "sources":
                results,
        }

    context = build_context(
        results
    )

    prompt = f"""
You are the grounded travel assistant for Around You,
a tourism application focused on Telangana, India.

Answer the user's question using ONLY the retrieved context.

RULES:
1. Use only the supplied context.
2. Do not invent facts.
3. Do not use outside knowledge.
4. If there is insufficient information, say that the
   Around You knowledge base does not contain enough information.
5. Mention destination names when relevant.
6. Keep the answer concise and useful.
7. Ignore retrieved sources that are not relevant to the question.

RETRIEVED CONTEXT:

{context}

USER QUESTION:

{question}

GROUNDED ANSWER:
"""

    try:

        client = (
            _get_gemini_client()
        )

        interaction = (
            client.interactions.create(
                model="gemini-3.6-flash",
                input=prompt,
            )
        )

        answer = (
            interaction.output_text
        )

        if not answer:

            answer = (
                "The relevant information was "
                "retrieved, but an answer could "
                "not be generated."
            )

    except Exception as exc:

        # Retrieval remains useful even if Gemini
        # quota/network/authentication is unavailable.

        answer = (
            "Relevant information was retrieved "
            "from the Around You knowledge base, "
            "but the generated answer is currently "
            "unavailable."
        )

    return {
        "question":
            question,

        "answer":
            answer.strip(),

        "sources":
            results,
    }