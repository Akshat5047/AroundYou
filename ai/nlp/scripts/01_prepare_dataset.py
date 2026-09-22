from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
NLP_DIR = SCRIPT_DIR.parent

DATASET_DIR = (
    NLP_DIR
    / "data"
    / "op_spam_v1.4"
    / "op_spam_v1.4"
)

OUTPUT_PATH = NLP_DIR / "data" / "reviews_clean.csv"


# ---------------------------------------------------------
# LOAD REVIEWS
# ---------------------------------------------------------

records = []

for file_path in DATASET_DIR.rglob("*.txt"):

    relative_parts = file_path.relative_to(DATASET_DIR).parts

    # We only want actual review files:
    # polarity/source/fold/file.txt
    if len(relative_parts) != 4:
        continue

    polarity_folder = relative_parts[0]
    source_folder = relative_parts[1]
    fold = relative_parts[2]

    # -------------------------
    # Sentiment
    # -------------------------

    if polarity_folder == "positive_polarity":
        sentiment = "positive"

    elif polarity_folder == "negative_polarity":
        sentiment = "negative"

    else:
        continue

    # -------------------------
    # Trust label
    # -------------------------

    if source_folder.startswith("deceptive"):
        label = "deceptive"

    elif source_folder.startswith("truthful"):
        label = "genuine"

    else:
        continue

    # -------------------------
    # Source
    # -------------------------

    if "TripAdvisor" in source_folder:
        source = "TripAdvisor"

    elif "Web" in source_folder:
        source = "Web"

    elif "MTurk" in source_folder:
        source = "MTurk"

    else:
        source = source_folder

    # -------------------------
    # Read review
    # -------------------------

    try:
        review = file_path.read_text(
            encoding="utf-8",
            errors="ignore"
        ).strip()

    except Exception as e:
        print(f"Could not read {file_path}: {e}")
        continue

    records.append(
        {
            "review": review,
            "label": label,
            "sentiment": sentiment,
            "source": source,
            "fold": fold,
            "filename": file_path.name,
        }
    )


# ---------------------------------------------------------
# CREATE DATAFRAME
# ---------------------------------------------------------

df = pd.DataFrame(records)


# ---------------------------------------------------------
# BASIC VALIDATION
# ---------------------------------------------------------

print("\n==============================")
print("DATASET VALIDATION")
print("==============================")

print(f"\nTotal reviews: {len(df)}")

print("\nColumns:")
print(df.columns.tolist())

print("\nMissing values:")
print(df.isnull().sum())

print("\nEmpty reviews:")
print((df["review"].str.strip() == "").sum())

print("\nDuplicate review texts:")
print(df["review"].duplicated().sum())


# ---------------------------------------------------------
# EDA
# ---------------------------------------------------------

df["word_count"] = (
    df["review"]
    .str.split()
    .str.len()
)

df["char_count"] = (
    df["review"]
    .str.len()
)


print("\n==============================")
print("CLASS DISTRIBUTION")
print("==============================")

print(df["label"].value_counts())


print("\n==============================")
print("SENTIMENT DISTRIBUTION")
print("==============================")

print(df["sentiment"].value_counts())


print("\n==============================")
print("LABEL × SENTIMENT")
print("==============================")

print(
    pd.crosstab(
        df["label"],
        df["sentiment"]
    )
)


print("\n==============================")
print("SOURCE DISTRIBUTION")
print("==============================")

print(df["source"].value_counts())


print("\n==============================")
print("FOLD DISTRIBUTION")
print("==============================")

print(df["fold"].value_counts().sort_index())


print("\n==============================")
print("REVIEW LENGTH STATISTICS")
print("==============================")

print(
    df.groupby("label")["word_count"]
    .describe()
    .round(2)
)


# ---------------------------------------------------------
# SAVE CLEAN DATASET
# ---------------------------------------------------------

df.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8"
)

print("\n==============================")
print("DATASET SAVED")
print("==============================")

print(OUTPUT_PATH)
print(f"\nFinal shape: {df.shape}")