from pathlib import Path
import joblib
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
NLP_DIR = SCRIPT_DIR.parent

DATA_PATH = NLP_DIR / "data" / "reviews_clean.csv"
MODEL_DIR = NLP_DIR / "models"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

df = pd.read_csv(DATA_PATH)

print("=" * 50)
print("REVIEW TRUST CLASSIFIER")
print("=" * 50)

print(f"\nDataset shape: {df.shape}")
print("\nLabels:")
print(df["label"].value_counts())


# ---------------------------------------------------------
# TRAIN / TEST SPLIT
#
# Use the corpus's existing folds:
# fold1-fold4 -> training
# fold5       -> testing
# ---------------------------------------------------------

train_df = df[df["fold"] != "fold5"].copy()
test_df = df[df["fold"] == "fold5"].copy()

print(f"\nTraining samples: {len(train_df)}")
print(f"Testing samples : {len(test_df)}")

print("\nTraining label distribution:")
print(train_df["label"].value_counts())

print("\nTesting label distribution:")
print(test_df["label"].value_counts())


X_train = train_df["review"]
y_train = train_df["label"]

X_test = test_df["review"]
y_test = test_df["label"]


# ---------------------------------------------------------
# TF-IDF
# ---------------------------------------------------------

vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2),
    max_features=20000,
    min_df=2,
    sublinear_tf=True
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)

print(f"\nTF-IDF training shape: {X_train_tfidf.shape}")
print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")


# ---------------------------------------------------------
# LOGISTIC REGRESSION
# ---------------------------------------------------------

model = LogisticRegression(
    max_iter=2000,
    random_state=42
)

model.fit(X_train_tfidf, y_train)


# ---------------------------------------------------------
# EVALUATION
# ---------------------------------------------------------

predictions = model.predict(X_test_tfidf)

accuracy = accuracy_score(
    y_test,
    predictions
)

print("\n" + "=" * 50)
print("MODEL EVALUATION")
print("=" * 50)

print(f"\nAccuracy: {accuracy:.4f}")

print("\nClassification Report:")
print(
    classification_report(
        y_test,
        predictions,
        digits=4
    )
)

print("Confusion Matrix:")
print(
    confusion_matrix(
        y_test,
        predictions,
        labels=["genuine", "deceptive"]
    )
)


# ---------------------------------------------------------
# SAVE MODEL
# ---------------------------------------------------------

MODEL_PATH = MODEL_DIR / "review_trust_model.pkl"
VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.pkl"

joblib.dump(
    model,
    MODEL_PATH
)

joblib.dump(
    vectorizer,
    VECTORIZER_PATH
)

print("\n" + "=" * 50)
print("MODEL SAVED")
print("=" * 50)

print(f"\nModel: {MODEL_PATH}")
print(f"Vectorizer: {VECTORIZER_PATH}")