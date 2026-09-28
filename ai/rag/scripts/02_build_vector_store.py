from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


# ============================================================
# PATHS
# ============================================================

RAG_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = (
    RAG_DIR
    / "data"
    / "destinations_knowledge.csv"
)

VECTOR_DIR = (
    RAG_DIR
    / "vector_store"
)

VECTOR_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

INDEX_PATH = (
    VECTOR_DIR
    / "destination.index"
)

METADATA_PATH = (
    VECTOR_DIR
    / "metadata.csv"
)


# ============================================================
# HEADER
# ============================================================

print("=" * 60)
print("AROUND YOU - RAG VECTOR STORE")
print("=" * 60)


# ============================================================
# 1. VALIDATE KNOWLEDGE BASE
# ============================================================

if not DATA_PATH.exists():

    raise FileNotFoundError(
        f"Knowledge base not found:\n{DATA_PATH}\n\n"
        "Run 01_prepare_knowledge_base.py first."
    )


# ============================================================
# 2. LOAD KNOWLEDGE BASE
# ============================================================

df = pd.read_csv(
    DATA_PATH
)

print()
print(
    f"Knowledge base: {DATA_PATH}"
)

print(
    f"Documents loaded: {len(df)}"
)


if df.empty:

    raise RuntimeError(
        "Knowledge base is empty."
    )


# ============================================================
# 3. VALIDATE REQUIRED COLUMNS
# ============================================================

required_columns = [
    "document_id",
    "spot_name",
    "district",
    "category",
    "knowledge_type",
    "content",
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:

    raise RuntimeError(
        "Knowledge base is missing required columns: "
        + ", ".join(missing_columns)
    )


# ============================================================
# 4. PREPARE TEXT FOR EMBEDDING
# ============================================================

print()
print(
    "Preparing destination documents..."
)


def build_embedding_text(row):

    spot_name = str(
        row.get(
            "spot_name",
            "",
        )
        or ""
    ).strip()

    district = str(
        row.get(
            "district",
            "",
        )
        or ""
    ).strip()

    category = str(
        row.get(
            "category",
            "",
        )
        or ""
    ).strip()

    content = str(
        row.get(
            "content",
            "",
        )
        or ""
    ).strip()

    return (
        f"Destination: {spot_name}. "
        f"District: {district}, Telangana. "
        f"Category: {category}. "
        f"{content}"
    )


documents = (
    df.apply(
        build_embedding_text,
        axis=1,
    )
    .tolist()
)


# ============================================================
# 5. LOAD EMBEDDING MODEL
# ============================================================

print()
print(
    "Loading embedding model..."
)

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


# ============================================================
# 6. GENERATE EMBEDDINGS
# ============================================================

print(
    "Generating embeddings..."
)

embeddings = model.encode(
    documents,
    convert_to_numpy=True,
    normalize_embeddings=True,
    show_progress_bar=True,
)

embeddings = embeddings.astype(
    np.float32
)

print(
    f"Embedding shape: {embeddings.shape}"
)


# ============================================================
# 7. VALIDATE EMBEDDINGS
# ============================================================

if len(embeddings) != len(df):

    raise RuntimeError(
        "Embedding count does not match "
        "knowledge-base document count."
    )


if embeddings.ndim != 2:

    raise RuntimeError(
        "Embeddings have an unexpected shape: "
        f"{embeddings.shape}"
    )


# ============================================================
# 8. CREATE FAISS INDEX
# ============================================================

dimension = embeddings.shape[1]

index = faiss.IndexFlatIP(
    dimension
)

index.add(
    embeddings
)


# ============================================================
# 9. VALIDATE INDEX
# ============================================================

if index.ntotal != len(df):

    raise RuntimeError(
        "FAISS index count does not match "
        "knowledge-base document count."
    )


# ============================================================
# 10. SAVE INDEX
# ============================================================

faiss.write_index(
    index,
    str(INDEX_PATH),
)


# ============================================================
# 11. SAVE METADATA
# ============================================================

df.to_csv(
    METADATA_PATH,
    index=False,
    encoding="utf-8",
)


# ============================================================
# 12. SUMMARY
# ============================================================

print()
print("=" * 60)
print("VECTOR STORE CREATED")
print("=" * 60)

print()
print(
    f"Vectors stored: {index.ntotal}"
)

print(
    f"Embedding dimension: {dimension}"
)

print(
    f"Districts represented: "
    f"{df['district'].nunique()}"
)

print(
    f"Categories represented: "
    f"{df['category'].nunique()}"
)

print()
print(
    f"FAISS index:\n{INDEX_PATH}"
)

print()
print(
    f"Metadata:\n{METADATA_PATH}"
)

print()
print("=" * 60)
print("RAG VECTOR STORE BUILD COMPLETE")
print("=" * 60)