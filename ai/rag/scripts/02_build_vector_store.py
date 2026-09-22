from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


RAG_DIR = Path(__file__).resolve().parent.parent

DATA_PATH = RAG_DIR / "data" / "destination_knowledge.csv"
VECTOR_DIR = RAG_DIR / "vector_store"

VECTOR_DIR.mkdir(parents=True, exist_ok=True)

INDEX_PATH = VECTOR_DIR / "destination.index"
METADATA_PATH = VECTOR_DIR / "metadata.csv"


print("=" * 50)
print("AROUND YOU - RAG VECTOR STORE")
print("=" * 50)


# --------------------------------------------------
# 1. Load knowledge base
# --------------------------------------------------

df = pd.read_csv(DATA_PATH)

print(f"\nDocuments loaded: {len(df)}")


# --------------------------------------------------
# 2. Prepare text for embedding
# --------------------------------------------------

documents = (
    df["spot_name"].fillna("")
    + ". "
    + df["category"].fillna("")
    + ". "
    + df["content"].fillna("")
).tolist()


# --------------------------------------------------
# 3. Load embedding model
# --------------------------------------------------

print("\nLoading embedding model...")

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


# --------------------------------------------------
# 4. Generate normalized embeddings
# --------------------------------------------------

print("Generating embeddings...")

embeddings = model.encode(
    documents,
    convert_to_numpy=True,
    normalize_embeddings=True,
    show_progress_bar=True
)

embeddings = embeddings.astype("float32")

print(f"Embedding shape: {embeddings.shape}")


# --------------------------------------------------
# 5. Create FAISS cosine-similarity index
# --------------------------------------------------

dimension = embeddings.shape[1]

index = faiss.IndexFlatIP(dimension)

index.add(embeddings)


# --------------------------------------------------
# 6. Save vector index + metadata
# --------------------------------------------------

faiss.write_index(
    index,
    str(INDEX_PATH)
)

df.to_csv(
    METADATA_PATH,
    index=False
)


print("\n" + "=" * 50)
print("VECTOR STORE CREATED")
print("=" * 50)

print(f"\nVectors stored: {index.ntotal}")
print(f"Embedding dimension: {dimension}")
print(f"FAISS index: {INDEX_PATH}")
print(f"Metadata: {METADATA_PATH}")