from pathlib import Path
from io import BytesIO

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageDraw


# ============================================================
# PATHS / SETTINGS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "cleanliness"
    / "best.onnx"
)

IMAGE_SIZE = 640
CONFIDENCE_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45

_session = None


# ============================================================
# MODEL LOADING
# ============================================================

def get_session():
    global _session

    if _session is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Cleanliness ONNX model not found: {MODEL_PATH}"
            )

        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1

        _session = ort.InferenceSession(
            str(MODEL_PATH),
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

    return _session


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image: Image.Image):
    image = image.convert("RGB")

    original_width, original_height = image.size

    scale = min(
        IMAGE_SIZE / original_width,
        IMAGE_SIZE / original_height,
    )

    resized_width = int(round(original_width * scale))
    resized_height = int(round(original_height * scale))

    resized = image.resize(
        (resized_width, resized_height),
        Image.Resampling.BILINEAR,
    )

    canvas = Image.new(
        "RGB",
        (IMAGE_SIZE, IMAGE_SIZE),
        (114, 114, 114),
    )

    pad_x = (IMAGE_SIZE - resized_width) // 2
    pad_y = (IMAGE_SIZE - resized_height) // 2

    canvas.paste(
        resized,
        (pad_x, pad_y),
    )

    array = np.asarray(
        canvas,
        dtype=np.float32,
    )

    array /= 255.0

    # HWC -> CHW
    array = np.transpose(
        array,
        (2, 0, 1),
    )

    array = np.expand_dims(
        array,
        axis=0,
    )

    array = np.ascontiguousarray(
        array,
        dtype=np.float32,
    )

    metadata = {
        "original_width": original_width,
        "original_height": original_height,
        "scale": scale,
        "pad_x": pad_x,
        "pad_y": pad_y,
    }

    return array, metadata


# ============================================================
# IOU / NMS
# ============================================================

def calculate_iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    intersection_width = max(0.0, x2 - x1)
    intersection_height = max(0.0, y2 - y1)

    intersection = (
        intersection_width
        * intersection_height
    )

    area1 = (
        max(0.0, box1[2] - box1[0])
        * max(0.0, box1[3] - box1[1])
    )

    area2 = (
        max(0.0, box2[2] - box2[0])
        * max(0.0, box2[3] - box2[1])
    )

    union = area1 + area2 - intersection

    if union <= 0:
        return 0.0

    return intersection / union


def non_max_suppression(detections):
    detections = sorted(
        detections,
        key=lambda item: item["confidence"],
        reverse=True,
    )

    selected = []

    while detections:
        current = detections.pop(0)

        selected.append(current)

        remaining = []

        for detection in detections:
            iou = calculate_iou(
                current["box"],
                detection["box"],
            )

            if iou < IOU_THRESHOLD:
                remaining.append(detection)

        detections = remaining

    return selected


# ============================================================
# YOLO OUTPUT PROCESSING
# ============================================================

def process_output(
    output,
    metadata,
):
    prediction = np.squeeze(output)

    # Typical one-class YOLOv8 ONNX output:
    #
    # (1, 5, 8400)
    #
    # After squeeze:
    #
    # (5, 8400)
    #
    # Convert to:
    #
    # (8400, 5)

    if (
        prediction.ndim == 2
        and prediction.shape[0] < prediction.shape[1]
    ):
        prediction = prediction.T

    detections = []

    original_width = metadata["original_width"]
    original_height = metadata["original_height"]
    scale = metadata["scale"]
    pad_x = metadata["pad_x"]
    pad_y = metadata["pad_y"]

    for row in prediction:
        if len(row) < 5:
            continue

        x_center = float(row[0])
        y_center = float(row[1])
        width = float(row[2])
        height = float(row[3])

        class_scores = row[4:]

        class_id = int(
            np.argmax(class_scores)
        )

        confidence = float(
            class_scores[class_id]
        )

        if confidence < CONFIDENCE_THRESHOLD:
            continue

        x1 = (
            x_center
            - width / 2
            - pad_x
        ) / scale

        y1 = (
            y_center
            - height / 2
            - pad_y
        ) / scale

        x2 = (
            x_center
            + width / 2
            - pad_x
        ) / scale

        y2 = (
            y_center
            + height / 2
            - pad_y
        ) / scale

        x1 = max(
            0.0,
            min(float(original_width), x1),
        )

        y1 = max(
            0.0,
            min(float(original_height), y1),
        )

        x2 = max(
            0.0,
            min(float(original_width), x2),
        )

        y2 = max(
            0.0,
            min(float(original_height), y2),
        )

        if x2 <= x1 or y2 <= y1:
            continue

        detections.append(
            {
                "class_id": class_id,
                "class_name": "Litter",
                "confidence": confidence,
                "box": [
                    x1,
                    y1,
                    x2,
                    y2,
                ],
            }
        )

    return non_max_suppression(
        detections
    )


# ============================================================
# CLEANLINESS SCORE
# ============================================================

def calculate_cleanliness(
    detections,
    image_width,
    image_height,
):
    """
    Calculate an application-level visible-litter indicator.

    This is NOT a direct output of the YOLO model.

    YOLO only detects visible litter.

    The score combines:
    1. Number of litter detections
    2. Detection confidence
    3. Approximate image area occupied by detected litter

    A score of 100 means no litter was detected.

    If litter is detected, the image will never be labelled
    completely "Clean".
    """

    # --------------------------------------------------------
    # NO LITTER DETECTED
    # --------------------------------------------------------

    if not detections:
        return {
            "score": 100.0,
            "status": "Clean",
            "coverage_percent": 0.0,
            "average_confidence": 0.0,
        }

    image_area = float(
        image_width
        * image_height
    )

    if image_area <= 0:
        image_area = 1.0

    # --------------------------------------------------------
    # DETECTION COUNT
    # --------------------------------------------------------

    detection_count = len(
        detections
    )

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    average_confidence = sum(
        detection["confidence"]
        for detection in detections
    ) / detection_count

    # --------------------------------------------------------
    # LITTER COVERAGE
    # --------------------------------------------------------

    total_litter_area = 0.0

    for detection in detections:
        x1, y1, x2, y2 = detection["box"]

        box_area = (
            max(0.0, x2 - x1)
            * max(0.0, y2 - y1)
        )

        # Confidence weighting reduces the impact of uncertain
        # detections.
        total_litter_area += (
            box_area
            * detection["confidence"]
        )

    coverage_ratio = min(
        total_litter_area / image_area,
        1.0,
    )

    coverage_percent = (
        coverage_ratio * 100.0
    )

    # --------------------------------------------------------
    # PENALTIES
    # --------------------------------------------------------

    # Every detected litter object contributes to the score.
    #
    # Cap prevents an extreme number of boxes from completely
    # dominating the result.
    count_penalty = min(
        detection_count * 7.0,
        42.0,
    )

    # Higher-confidence detections should have greater impact.
    confidence_penalty = min(
        average_confidence * 10.0,
        10.0,
    )

    # Larger visible litter regions should have greater impact.
    coverage_penalty = min(
        coverage_ratio * 250.0,
        38.0,
    )

    total_penalty = (
        count_penalty
        + confidence_penalty
        + coverage_penalty
    )

    score = (
        100.0
        - total_penalty
    )

    score = max(
        0.0,
        min(100.0, score),
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    # Important:
    #
    # Any detected litter prevents the result from being
    # labelled "Clean".

    if score >= 70:
        status = "Light Litter"

    elif score >= 45:
        status = "Moderate Litter"

    else:
        status = "Heavy Litter"

    return {
        "score": round(score, 1),
        "status": status,
        "coverage_percent": round(
            coverage_percent,
            2,
        ),
        "average_confidence": round(
            average_confidence,
            4,
        ),
    }


# ============================================================
# ANNOTATED IMAGE
# ============================================================

def create_annotated_image(
    image,
    detections,
):
    annotated = image.copy().convert("RGB")

    draw = ImageDraw.Draw(
        annotated
    )

    for detection in detections:
        x1, y1, x2, y2 = detection["box"]

        confidence = (
            detection["confidence"]
        )

        draw.rectangle(
            [x1, y1, x2, y2],
            outline="red",
            width=4,
        )

        label = (
            f"Litter {confidence:.0%}"
        )

        text_y = max(
            0,
            y1 - 18,
        )

        draw.text(
            (x1 + 2, text_y),
            label,
            fill="red",
        )

    output = BytesIO()

    annotated.save(
        output,
        format="JPEG",
        quality=90,
    )

    return output.getvalue()


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_cleanliness(
    image_bytes: bytes,
):
    try:
        image = Image.open(
            BytesIO(image_bytes)
        )

        image.load()

    except Exception as exc:
        raise ValueError(
            "The uploaded file is not a valid image."
        ) from exc

    image = image.convert("RGB")

    tensor, metadata = preprocess_image(
        image
    )

    session = get_session()

    input_name = (
        session.get_inputs()[0].name
    )

    outputs = session.run(
        None,
        {
            input_name: tensor
        },
    )

    detections = process_output(
        outputs[0],
        metadata,
    )

    cleanliness = calculate_cleanliness(
        detections,
        image.width,
        image.height,
    )

    annotated_bytes = create_annotated_image(
        image,
        detections,
    )

    clean_detections = []

    for detection in detections:
        clean_detections.append(
            {
                "class_id": (
                    detection["class_id"]
                ),
                "class_name": (
                    detection["class_name"]
                ),
                "confidence": round(
                    detection["confidence"],
                    4,
                ),
                "box": [
                    round(value, 2)
                    for value
                    in detection["box"]
                ],
            }
        )

    return {
        "cleanliness_score": (
            cleanliness["score"]
        ),
        "status": (
            cleanliness["status"]
        ),
        "litter_count": len(
            clean_detections
        ),
        "litter_coverage_percent": (
            cleanliness[
                "coverage_percent"
            ]
        ),
        "average_confidence": (
            cleanliness[
                "average_confidence"
            ]
        ),
        "detections": (
            clean_detections
        ),
        "annotated_image": (
            annotated_bytes
        ),
        "disclaimer": (
            "This is an AI-generated visible-litter indicator "
            "based only on litter detected in the uploaded "
            "image. It does not represent the overall "
            "cleanliness of the entire location."
        ),
    }