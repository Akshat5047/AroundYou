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

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
RAG_DIR = PROJECT_DIR / "ai" / "rag"

INDEX_PATH = RAG_DIR / "vector_store" / "destination.index"
METADATA_PATH = RAG_DIR / "vector_store" / "metadata.csv"

load_dotenv(PROJECT_DIR / ".env")


# ==================================================
# GEMINI
# ==================================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in AroundYou/.env")

client = genai.Client(api_key=api_key)


# ==================================================
# LOAD RAG COMPONENTS ONCE
# ==================================================

index = faiss.read_index(str(INDEX_PATH))
metadata = pd.read_csv(METADATA_PATH)

embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


# ==================================================
# RETRIEVAL
# ==================================================

def retrieve_documents(question: str, top_k: int = 3):

    query_embedding = embedding_model.encode(
        [question],
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
            "document_id": str(row["document_id"]),
            "spot_name": str(row["spot_name"]),
            "district": str(row["district"]),
            "category": str(row["category"]),
            "knowledge_type": str(row["knowledge_type"]),
            "content": str(row["content"]),
            "similarity": float(score)
        })

    return results


# ==================================================
# CONTEXT
# ==================================================

def build_context(results):

    sections = []

    for number, result in enumerate(results, start=1):

        sections.append(
            f"""
Source {number}
Destination: {result['spot_name']}
District: {result['district']}
Category: {result['category']}
Information: {result['content']}
""".strip()
        )

    return "\n\n".join(sections)


# ==================================================
# RAG
# ==================================================

def answer_question(question: str, top_k: int = 3):

    results = retrieve_documents(
        question=question,
        top_k=top_k
    )

    if not results or results[0]["similarity"] < 0.25:

        return {
            "question": question,
            "answer": (
                "I don't have enough relevant information in "
                "the Around You knowledge base to answer that reliably."
            ),
            "sources": results
        }

    context = build_context(results)

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

    interaction = client.interactions.create(
        model="gemini-3.6-flash",
        input=prompt
    )

    answer = interaction.output_text

    if not answer:
        answer = (
            "The relevant information was retrieved, "
            "but an answer could not be generated."
        )

    return {
        "question": question,
        "answer": answer.strip(),
        "sources": results
    }