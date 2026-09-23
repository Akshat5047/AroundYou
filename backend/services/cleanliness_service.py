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

        # Keep memory/CPU usage controlled on Render.
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

    # Add batch dimension.
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

    area1 = max(
        0.0,
        box1[2] - box1[0],
    ) * max(
        0.0,
        box1[3] - box1[1],
    )

    area2 = max(
        0.0,
        box2[2] - box2[0],
    ) * max(
        0.0,
        box2[3] - box2[1],
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

    # Typical YOLOv8 ONNX output:
    # (1, 5, 8400) for one-class detector.
    #
    # After squeeze:
    # (5, 8400)
    #
    # Convert to:
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
    Application-level cleanliness indicator.

    This is NOT an objective measurement of the physical
    cleanliness of an entire tourist destination.

    The score is based only on visible litter detected in the
    uploaded image.
    """

    image_area = float(
        image_width
        * image_height
    )

    if image_area <= 0:
        return 100.0, "Clean"

    litter_area = 0.0

    for detection in detections:
        x1, y1, x2, y2 = detection["box"]

        area = max(
            0.0,
            x2 - x1,
        ) * max(
            0.0,
            y2 - y1,
        )

        # Confidence-weighted visible litter area.
        litter_area += (
            area
            * detection["confidence"]
        )

    coverage = min(
        litter_area / image_area,
        1.0,
    )

    detection_penalty = min(
        len(detections) * 4.0,
        35.0,
    )

    coverage_penalty = min(
        coverage * 300.0,
        55.0,
    )

    score = (
        100.0
        - detection_penalty
        - coverage_penalty
    )

    score = max(
        0.0,
        min(100.0, score),
    )

    if score >= 80:
        status = "Clean"

    elif score >= 55:
        status = "Moderate"

    else:
        status = "Poor"

    return round(score, 1), status


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

    score, status = calculate_cleanliness(
        detections,
        image.width,
        image.height,
    )

    annotated_bytes = create_annotated_image(
        image,
        detections,
    )

    # Round values before returning them.
    clean_detections = []

    for detection in detections:
        clean_detections.append(
            {
                "class_id": detection["class_id"],
                "class_name": detection["class_name"],
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
        "cleanliness_score": score,
        "status": status,
        "litter_count": len(
            clean_detections
        ),
        "detections": clean_detections,
        "annotated_image": annotated_bytes,
        "disclaimer": (
            "This cleanliness indicator is based only on "
            "visible litter detected in the uploaded image. "
            "It is not an objective assessment of the entire "
            "location."
        ),
    }