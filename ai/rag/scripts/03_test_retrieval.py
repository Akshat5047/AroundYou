from pathlib import Path

import faiss
import pandas as pd
from sentence_transformers import SentenceTransformer


RAG_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = RAG_DIR / "vector_store" / "destination.index"
METADATA_PATH = RAG_DIR / "vector_store" / "metadata.csv"


print("=" * 55)
print("AROUND YOU - SEMANTIC RETRIEVAL TEST")
print("=" * 55)


# Load vector store
index = faiss.read_index(str(INDEX_PATH))
metadata = pd.read_csv(METADATA_PATH)

# Same embedding model used when building the index
model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


def search(query, top_k=3):

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype("float32")

    scores, indices = index.search(
        query_embedding,
        min(top_k, index.ntotal)
    )

    results = []

    for score, idx in zip(scores[0], indices[0]):

        if idx == -1:
            continue

        row = metadata.iloc[idx]

        results.append({
            "spot_name": row["spot_name"],
            "district": row["district"],
            "category": row["category"],
            "content": row["content"],
            "similarity": float(score)
        })

    return results


# Test query
query = "historic Kakatiya temple with sculptures"

print(f"\nQuery: {query}")

results = search(query)

for rank, result in enumerate(results, start=1):

    print("\n" + "-" * 55)
    print(f"RESULT {rank}")
    print("-" * 55)

    print(f"Spot       : {result['spot_name']}")
    print(f"District   : {result['district']}")
    print(f"Category   : {result['category']}")
    print(f"Similarity : {result['similarity']:.4f}")
    print(f"Content    : {result['content']}")