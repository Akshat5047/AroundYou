from pathlib import Path
import os

import faiss
import pandas as pd
from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer


# ==================================================
# PATHS
# ==================================================

PROJECT_DIR = Path(__file__).resolve().parents[3]
RAG_DIR = Path(__file__).resolve().parent.parent

INDEX_PATH = RAG_DIR / "vector_store" / "destination.index"
METADATA_PATH = RAG_DIR / "vector_store" / "metadata.csv"

load_dotenv(PROJECT_DIR / ".env")


# ==================================================
# GEMINI CLIENT
# ==================================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. "
        "Make sure it exists in the AroundYou/.env file."
    )

client = genai.Client(api_key=api_key)


# ==================================================
# LOAD RAG COMPONENTS
# ==================================================

print("=" * 55)
print("AROUND YOU - RAG GENERATION TEST")
print("=" * 55)

print("\nLoading RAG components...")

index = faiss.read_index(str(INDEX_PATH))

metadata = pd.read_csv(METADATA_PATH)

embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

print(f"FAISS vectors loaded: {index.ntotal}")
print(f"Metadata documents: {len(metadata)}")


# ==================================================
# RETRIEVAL
# ==================================================

def retrieve(query: str, top_k: int = 3):

    query_embedding = embedding_model.encode(
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
            "document_id": row["document_id"],
            "spot_name": row["spot_name"],
            "district": row["district"],
            "category": row["category"],
            "knowledge_type": row["knowledge_type"],
            "content": row["content"],
            "similarity": float(score)
        })

    return results


# ==================================================
# BUILD CONTEXT
# ==================================================

def build_context(results):

    context_parts = []

    for number, result in enumerate(results, start=1):

        context_parts.append(
            f"""
Source {number}

Destination: {result['spot_name']}
District: {result['district']}
Category: {result['category']}
Knowledge Type: {result['knowledge_type']}
Information: {result['content']}
""".strip()
        )

    return "\n\n".join(context_parts)


# ==================================================
# RAG QUESTION ANSWERING
# ==================================================

def ask_rag(question: str, top_k: int = 3):

    # ----------------------------------------------
    # 1. Retrieve relevant documents
    # ----------------------------------------------

    results = retrieve(
        query=question,
        top_k=top_k
    )

    if not results:

        return {
            "answer": (
                "I don't have enough information in the "
                "Around You knowledge base to answer that reliably."
            ),
            "sources": []
        }

    # ----------------------------------------------
    # 2. Relevance guard
    # ----------------------------------------------

    best_similarity = results[0]["similarity"]

    if best_similarity < 0.25:

        return {
            "answer": (
                "I don't have enough relevant information in the "
                "Around You knowledge base to answer that reliably."
            ),
            "sources": results
        }

    # ----------------------------------------------
    # 3. Build grounded context
    # ----------------------------------------------

    context = build_context(results)

    # ----------------------------------------------
    # 4. Create grounded prompt
    # ----------------------------------------------

    prompt = f"""
You are the grounded travel assistant for Around You,
a tourism application focused on Telangana, India.

Your task is to answer the user's question using ONLY
the information provided in the retrieved context below.

IMPORTANT RULES:

1. Use only the supplied context.
2. Do not invent destinations, facts, timings, prices,
   historical details, facilities, or recommendations.
3. Do not use outside knowledge even if you know the answer.
4. If the context does not contain enough information,
   clearly say that the Around You knowledge base does not
   contain enough information.
5. Mention the destination names used in your answer.
6. Keep the answer concise, clear, and useful for a traveler.
7. If multiple destinations in the context are relevant,
   you may mention more than one.
8. Do not claim that retrieved information is verified unless
   the context explicitly says so.

RETRIEVED CONTEXT:

{context}

USER QUESTION:

{question}

GROUNDED ANSWER:
"""

    # ----------------------------------------------
    # 5. Gemini generation
    # ----------------------------------------------

    try:

        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            input=prompt
        )

        answer = interaction.output_text

        if not answer:
            answer = (
                "The retrieved information was relevant, "
                "but the language model did not return an answer."
            )

    except Exception as error:

        print("\nGemini generation error:")
        print(error)

        raise

    # ----------------------------------------------
    # 6. Return answer + sources
    # ----------------------------------------------

    return {
        "answer": answer.strip(),
        "sources": results
    }


# ==================================================
# TEST
# ==================================================

if __name__ == "__main__":

    question = (
        "Which destination should I consider if I want "
        "to see Kakatiya architecture and sculptures?"
    )

    print("\nQuestion:")
    print(question)

    result = ask_rag(question)

    print("\n" + "=" * 55)
    print("RAG ANSWER")
    print("=" * 55)

    print(result["answer"])

    print("\n" + "=" * 55)
    print("RETRIEVED SOURCES")
    print("=" * 55)

    for number, source in enumerate(
        result["sources"],
        start=1
    ):

        print(f"\nSource {number}")
        print(f"Spot       : {source['spot_name']}")
        print(f"District   : {source['district']}")
        print(f"Category   : {source['category']}")
        print(
            f"Similarity : "
            f"{source['similarity']:.4f}"
        )