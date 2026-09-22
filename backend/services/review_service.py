import os
import joblib


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models",
    "nlp"
)


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


CONFIDENCE_THRESHOLD = 0.70


def classify_review(review: str):

    # Convert text to TF-IDF features
    X = vectorizer.transform([review])

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
        "probabilities": probability_map
    }