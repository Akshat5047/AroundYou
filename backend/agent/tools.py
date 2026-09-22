from pathlib import Path
from functools import lru_cache

from services.review_service import classify_review
from services.budget_service import predict_budget
from services.climate_service import predict_climate
from services.crowd_service import predict_crowd
from services.transport_service import predict_transport


# ============================================================
# PATHS
# ============================================================

BACKEND_DIR = Path(
    __file__
).resolve().parent.parent

PROJECT_DIR = BACKEND_DIR.parent

RAG_DIR = (
    PROJECT_DIR /
    "ai" /
    "rag"
)

INDEX_PATH = (
    RAG_DIR /
    "vector_store" /
    "destination.index"
)

METADATA_PATH = (
    RAG_DIR /
    "vector_store" /
    "metadata.csv"
)


# ============================================================
# LAZY RAG COMPONENTS
# ============================================================

@lru_cache(maxsize=1)
def _get_rag_resources():

    import faiss
    import pandas as pd

    from sentence_transformers import (
        SentenceTransformer
    )

    rag_index = faiss.read_index(
        str(INDEX_PATH)
    )

    rag_metadata = pd.read_csv(
        METADATA_PATH
    )

    embedding_model = SentenceTransformer(
        "sentence-transformers/"
        "all-MiniLM-L6-v2"
    )

    return (
        rag_index,
        rag_metadata,
        embedding_model
    )


# ============================================================
# DIRECT RAG RETRIEVAL
# ============================================================

def search_destination_knowledge(
    query: str,
    top_k: int = 10
):

    (
        rag_index,
        rag_metadata,
        embedding_model
    ) = _get_rag_resources()

    query_embedding = embedding_model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    search_count = min(
        top_k,
        rag_index.ntotal
    )

    scores, indices = rag_index.search(
        query_embedding,
        search_count
    )

    results = []

    for score, idx in zip(
        scores[0],
        indices[0]
    ):

        if idx == -1:
            continue

        row = rag_metadata.iloc[idx]

        results.append({
            "document_id": str(
                row["document_id"]
            ),

            "spot_name": str(
                row["spot_name"]
            ),

            "district": str(
                row["district"]
            ),

            "category": str(
                row["category"]
            ),

            "knowledge_type": str(
                row["knowledge_type"]
            ),

            "content": str(
                row["content"]
            ),

            "similarity": float(score)
        })

    return {
        "query": query,
        "sources": results
    }


# ============================================================
# NLP REVIEW TRUST
# ============================================================

def check_review_trust(
    review_text: str
):

    return classify_review(
        review_text
    )


# ============================================================
# BUDGET ML
# ============================================================

def run_budget_prediction(
    duration_days,
    num_travelers,
    route_distance_km,
    accommodation_tier,
    transport_mode,
    season
):

    data = {
        "duration_days": duration_days,
        "num_travelers": num_travelers,
        "route_distance_km": route_distance_km,
        "accommodation_tier": accommodation_tier,
        "transport_mode": transport_mode,
        "season": season
    }

    result = predict_budget(data)

    if not isinstance(result, dict):
        return result

    if result.get("error"):
        return result

    # --------------------------------------------------------
    # COST CLEANUP
    # --------------------------------------------------------

    cost_fields = [
        "travel_cost_est",
        "stay_cost_est",
        "food_cost_est",
        "entry_fees_est",
        "tolls_and_parking_est"
    ]

    cleaned = dict(result)

    for field in cost_fields:

        value = cleaned.get(field)

        if isinstance(
            value,
            (int, float)
        ):

            cleaned[field] = max(
                0.0,
                float(value)
            )

    available_costs = [
        cleaned[field]
        for field in cost_fields
        if isinstance(
            cleaned.get(field),
            (int, float)
        )
    ]

    if len(available_costs) == len(
        cost_fields
    ):

        cleaned[
            "predicted_total_cost"
        ] = sum(
            available_costs
        )

    return cleaned


# ============================================================
# CLIMATE ML
# ============================================================

def run_climate_prediction(
    district,
    forecast_date
):

    data = {
        "district": district,
        "forecast_date": forecast_date
    }

    return predict_climate(data)


# ============================================================
# CROWD ML
# ============================================================

def run_crowd_prediction(
    spot_name,
    district,
    category,
    year,
    month,
    season,
    festival
):

    data = {
        "spot_name": spot_name,
        "district": district,
        "category": category,
        "year": year,
        "month": month,
        "season": season,
        "festival": festival
    }

    return predict_crowd(data)


# ============================================================
# TRANSPORT ML
# ============================================================

def run_transport_prediction(
    distance_km,
    budget_limit,
    num_people,
    rainfall_mm,
    road_access_rating
):

    data = {
        "distance_km": distance_km,
        "budget_limit": budget_limit,
        "num_people": num_people,
        "rainfall_mm": rainfall_mm,
        "road_access_rating": road_access_rating
    }

    return predict_transport(data)