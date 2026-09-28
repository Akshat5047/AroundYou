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
# RESULT CONVERSION
# ============================================================

def _metadata_row_to_result(
    row,
    similarity,
):

    return {
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
                similarity
            ),
    }

# ============================================================
# EXACT DESTINATION RETRIEVAL
# ============================================================

def retrieve_selected_destinations(
    selected_destinations
):

    (
        _,
        metadata,
        _,
        _,
    ) = _get_rag_resources()

    results = []

    for selected in (
        selected_destinations or []
    ):

        selected_id = str(
            selected.get("id") or ""
        ).strip()

        selected_name = str(
            selected.get("name") or ""
        ).strip().lower()

        selected_district = str(
            selected.get("district") or ""
        ).strip().lower()

        match = None

        # Prefer exact document ID.
        if selected_id:

            id_matches = metadata[
                metadata["document_id"]
                .astype(str)
                .str.strip()
                == selected_id
            ]

            if not id_matches.empty:
                match = id_matches.iloc[0]

        # Fall back to exact name + district.
        if (
            match is None
            and selected_name
        ):

            name_matches = metadata[
                metadata["spot_name"]
                .astype(str)
                .str.strip()
                .str.lower()
                == selected_name
            ]

            if selected_district:

                name_matches = name_matches[
                    name_matches["district"]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    == selected_district
                ]

            if not name_matches.empty:
                match = name_matches.iloc[0]

        if match is None:
            continue

        results.append(
            _metadata_row_to_result(
                row=match,
                similarity=1.0
            )
        )

    return results

# ============================================================
# STANDARD FAISS RETRIEVAL
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
        max(
            1,
            int(top_k)
        ),
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
            _metadata_row_to_result(
                row=row,
                similarity=score,
            )
        )

    return results


# ============================================================
# METADATA-FILTERED FAISS RETRIEVAL
# ============================================================

def retrieve_documents_by_districts(
    question: str,
    districts,
    top_k: int = 10,
):

    """
    Retrieve destinations only from the supplied districts.

    The full FAISS index remains the source of semantic similarity,
    but the search is expanded across the complete index before
    applying the district restriction.

    This prevents relevant destinations from being lost simply
    because they did not appear inside a small global top-k result.
    """

    (
        index,
        metadata,
        _,
        _,
    ) = _get_rag_resources()

    # --------------------------------------------------------
    # NORMALIZE DISTRICTS
    # --------------------------------------------------------

    allowed_districts = {
        str(district)
        .strip()
        .lower()

        for district in (
            districts or []
        )

        if str(
            district
        ).strip()
    }

    # No district restriction supplied.
    # Fall back to normal semantic retrieval.

    if not allowed_districts:

        return retrieve_documents(
            question=question,
            top_k=top_k,
        )

    # --------------------------------------------------------
    # QUERY EMBEDDING
    # --------------------------------------------------------

    query_embedding = (
        create_query_embedding(
            question
        )
    )

    # --------------------------------------------------------
    # SEARCH COMPLETE INDEX
    # --------------------------------------------------------
    #
    # There are currently only 271 destination vectors.
    # Searching the full index is inexpensive and guarantees
    # that allowed-district destinations are available for
    # filtering.
    # --------------------------------------------------------

    search_count = (
        index.ntotal
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

        row_district = (
            str(
                row[
                    "district"
                ]
            )
            .strip()
            .lower()
        )

        if (
            row_district
            not in allowed_districts
        ):

            continue

        results.append(
            _metadata_row_to_result(
                row=row,
                similarity=score,
            )
        )

        if len(
            results
        ) >= max(
            1,
            int(top_k)
        ):

            break

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

    except Exception:

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