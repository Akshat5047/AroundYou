from pathlib import Path
import json
import sqlite3

import pandas as pd


# ============================================================
# PATHS
# ============================================================

# Current file:
# AroundYou/ai/rag/scripts/prepare_knowledge_base.py

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DB_PATH = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "smart_tourism.db"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "ai"
    / "rag"
    / "data"
    / "destinations_knowledge.csv"
)


# ============================================================
# HELPERS
# ============================================================

def clean_text(value):
    """
    Convert database values into clean text.
    """

    if value is None:
        return ""

    return str(value).strip()


def format_entry_fee(value):
    """
    Convert entry fee into human-readable text.
    """

    if value is None:
        return "Entry fee information is unavailable"

    try:
        fee = float(value)
    except (TypeError, ValueError):
        return "Entry fee information is unavailable"

    if fee <= 0:
        return "Entry is free"

    if fee.is_integer():
        return f"Entry fee is approximately ₹{int(fee)}"

    return f"Entry fee is approximately ₹{fee:.2f}"


def format_rating(value):
    """
    Format destination rating.
    """

    if value is None:
        return "Rating information is unavailable"

    try:
        rating = float(value)
        return f"It has a rating of {rating:.1f} out of 5"
    except (TypeError, ValueError):
        return "Rating information is unavailable"


def extract_reviews(review_value, limit=2):
    """
    Extract useful review text from the JSON stored in
    the other_spots.reviews column.

    Expected structure:
    [
        ["Reviewer Name", "Review text"],
        ["Reviewer Name", "Review text"]
    ]
    """

    if not review_value:
        return []

    try:
        reviews = json.loads(review_value)
    except (TypeError, json.JSONDecodeError):
        return []

    extracted = []

    if not isinstance(reviews, list):
        return extracted

    for review in reviews:

        if len(extracted) >= limit:
            break

        if isinstance(review, list) and len(review) >= 2:

            review_text = clean_text(review[1])

            if review_text:
                extracted.append(review_text)

        elif isinstance(review, dict):

            review_text = clean_text(
                review.get("review")
                or review.get("text")
                or review.get("comment")
            )

            if review_text:
                extracted.append(review_text)

    return extracted


def build_content(row):
    """
    Create natural-language destination knowledge
    for embedding and Gemini grounding.
    """

    name = clean_text(row["name"])
    district = clean_text(row["district"])
    category = clean_text(row["category"])

    if not district:
        district = "Telangana"

    if not category:
        category = "tourist attraction"

    sentences = [
        (
            f"{name} is a {category} tourist destination "
            f"in {district}, Telangana."
        )
    ]

    # --------------------------------------------------------
    # Rating
    # --------------------------------------------------------

    rating_text = format_rating(
        row["rating"]
    )

    sentences.append(
        rating_text + "."
    )

    # --------------------------------------------------------
    # Popularity
    # --------------------------------------------------------

    popularity = row["popularity"]

    if popularity is not None:

        try:
            popularity_value = int(
                float(popularity)
            )

            sentences.append(
                f"Its recorded popularity score is "
                f"{popularity_value}."
            )

        except (TypeError, ValueError):
            pass

    # --------------------------------------------------------
    # Entry fee
    # --------------------------------------------------------

    entry_fee_text = format_entry_fee(
        row["entry_fee"]
    )

    sentences.append(
        entry_fee_text + "."
    )

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    lat = row["lat"]
    lon = row["lon"]

    if lat is not None and lon is not None:

        try:

            latitude = float(lat)
            longitude = float(lon)

            sentences.append(
                f"The destination is located near "
                f"latitude {latitude:.4f} and "
                f"longitude {longitude:.4f}."
            )

        except (TypeError, ValueError):
            pass

    # --------------------------------------------------------
    # Reviews
    # --------------------------------------------------------

    reviews = extract_reviews(
        row["reviews"]
    )

    if reviews:

        review_text = " ".join(
            f'Visitor feedback includes: "{review}"'
            for review in reviews
        )

        sentences.append(
            review_text
        )

    return " ".join(sentences)


# ============================================================
# LOAD DESTINATIONS
# ============================================================

def load_destinations():

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found:\n{DB_PATH}"
        )

    connection = sqlite3.connect(
        DB_PATH
    )

    try:

        query = """
            SELECT
                id,
                name,
                district,
                category,
                rating,
                popularity,
                entry_fee,
                lat,
                lon,
                reviews
            FROM other_spots
            WHERE name IS NOT NULL
              AND TRIM(name) != ''
            ORDER BY
                district ASC,
                popularity DESC,
                rating DESC,
                name ASC
        """

        dataframe = pd.read_sql_query(
            query,
            connection,
        )

    finally:

        connection.close()

    return dataframe


# ============================================================
# PREPARE KNOWLEDGE BASE
# ============================================================

def prepare_knowledge_base():

    print("=" * 60)
    print("AROUND YOU - RAG KNOWLEDGE BASE PREPARATION")
    print("=" * 60)

    print()
    print(
        f"Database:\n{DB_PATH}"
    )

    # --------------------------------------------------------
    # Read database
    # --------------------------------------------------------

    destinations = load_destinations()

    print()
    print(
        f"Loaded {len(destinations)} destinations "
        f"from other_spots."
    )

    if destinations.empty:

        raise RuntimeError(
            "No destinations were found in other_spots."
        )

    # --------------------------------------------------------
    # Create knowledge documents
    # --------------------------------------------------------

    documents = []

    for index, row in destinations.iterrows():

        document_id = (
            f"destination_{index + 1:04d}"
        )

        documents.append(
            {
                "document_id":
                    document_id,

                "spot_id":
                    row["id"],

                "spot_name":
                    clean_text(
                        row["name"]
                    ),

                "district":
                    clean_text(
                        row["district"]
                    ),

                "category":
                    clean_text(
                        row["category"]
                    ),

                "knowledge_type":
                    "destination",

                "content":
                    build_content(row),
            }
        )

    knowledge_df = pd.DataFrame(
        documents
    )

    # --------------------------------------------------------
    # Remove accidental duplicate destinations
    # --------------------------------------------------------

    knowledge_df = (
        knowledge_df
        .drop_duplicates(
            subset=[
                "spot_name",
                "district",
            ],
            keep="first",
        )
        .reset_index(drop=True)
    )

    # Regenerate sequential document IDs after deduplication.
    knowledge_df["document_id"] = [
        f"destination_{i + 1:04d}"
        for i in range(
            len(knowledge_df)
        )
    ]

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    knowledge_df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print(
        f"Knowledge documents created: "
        f"{len(knowledge_df)}"
    )

    print(
        f"Districts represented: "
        f"{knowledge_df['district'].nunique()}"
    )

    print(
        f"Categories represented: "
        f"{knowledge_df['category'].nunique()}"
    )

    print()
    print(
        "Knowledge base saved to:"
    )

    print(
        OUTPUT_PATH
    )

    print()
    print("=" * 60)
    print("SAMPLE KNOWLEDGE DOCUMENTS")
    print("=" * 60)

    sample_columns = [
        "document_id",
        "spot_name",
        "district",
        "category",
    ]

    print(
        knowledge_df[
            sample_columns
        ]
        .head(10)
        .to_string(index=False)
    )

    print()
    print("=" * 60)
    print("KNOWLEDGE BASE PREPARATION COMPLETE")
    print("=" * 60)

    return knowledge_df


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    prepare_knowledge_base()