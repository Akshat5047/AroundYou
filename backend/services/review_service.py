import os
import re
from functools import lru_cache


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models",
    "nlp"
)


# ============================================================
# SETTINGS
# ============================================================

CONFIDENCE_THRESHOLD = 0.70


# ============================================================
# LAZY MODEL LOADER
# ============================================================

@lru_cache(maxsize=1)
def _get_review_resources():
    import joblib

    model = joblib.load(
        os.path.join(
            MODEL_DIR,
            "review_trust_model.pkl"
        )
    )

    vectorizer = joblib.load(
        os.path.join(
            MODEL_DIR,
            "tfidf_vectorizer.pkl"
        )
    )

    return model, vectorizer


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_review(review: str):

    words = re.findall(r"\b[^\W\d_]+\b", review, flags=re.UNICODE)
    def insufficient(reason):
        return {"label": "unverified", "predicted_class": None,
                "confidence": None, "threshold": CONFIDENCE_THRESHOLD,
                "probabilities": {}, "reason": reason}

    if len(words) < 10:
        return insufficient("Please provide a fuller review (at least 10 words) describing the visit or stay. There is too little text to assess its wording.")

    model, vectorizer = _get_review_resources()

    # Convert text to TF-IDF features
    X = vectorizer.transform([review])
    if X.nnz == 0:
        return insufficient("The model does not recognize enough of this wording. Try a detailed review in English.")

    # Predict probabilities
    probabilities = model.predict_proba(X)[0]

    classes = model.classes_

    probability_map = {
        str(label): float(probability)
        for label, probability
        in zip(classes, probabilities)
    }

    # Highest probability class
    best_index = probabilities.argmax()

    predicted_class = str(
        classes[best_index]
    )

    confidence = float(
        probabilities[best_index]
    )

    # Application-level abstention
    if confidence < CONFIDENCE_THRESHOLD:
        final_label = "unverified"
    else:
        final_label = predicted_class

    return {
        "label": final_label,
        "predicted_class": predicted_class,
        "confidence": confidence,
        "threshold": CONFIDENCE_THRESHOLD,
        "probabilities": probability_map,
        "reason": (
            "Neither class reached the 70% decision threshold. The wording is inconclusive; this does not mean the review is fake."
            if final_label == "unverified" else
            "The wording more closely matches the model's " + final_label + " review examples. This is a language-pattern assessment, not a verification of the experience."
        )
    }
