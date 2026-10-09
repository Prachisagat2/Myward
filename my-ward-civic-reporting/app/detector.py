"""Optional YOLOv8 issue detector.

The server works without it (citizens pick the category). If ultralytics is
installed and a trained model exists at MYWARD_MODEL_PATH, a complaint can be
submitted with only a photo and the category is detected automatically.
"""
import importlib.util
import io
import os
import threading
from dataclasses import dataclass
from pathlib import Path

from . import config
from .enums import Category

MODEL_PATH = Path(os.getenv("MYWARD_MODEL_PATH", str(config.BASE_DIR / "models" / "best.pt")))
MIN_CONFIDENCE = float(os.getenv("MYWARD_MIN_CONFIDENCE", "0.4"))

# Model class label (lower-case) -> complaint category. Add aliases to match
# the class names in YOUR dataset.
LABEL_TO_CATEGORY: dict[str, Category] = {
    "pothole": Category.POTHOLE,
    "potholes": Category.POTHOLE,
    "garbage": Category.GARBAGE,
    "trash": Category.GARBAGE,
    "waste": Category.GARBAGE,
    "streetlight": Category.STREETLIGHT,
    "street_light": Category.STREETLIGHT,
    "broken_streetlight": Category.STREETLIGHT,
    "water_leakage": Category.WATER_LEAKAGE,
    "water_leak": Category.WATER_LEAKAGE,
    "drainage": Category.DRAINAGE,
    "drain": Category.DRAINAGE,
    "illegal_dumping": Category.ILLEGAL_DUMPING,
    "dumping": Category.ILLEGAL_DUMPING,
}


class DetectorUnavailable(Exception):
    """Raised when YOLO or the trained model is not set up."""


@dataclass
class Detection:
    category: Category
    confidence: float


def map_label(label: str) -> Category | None:
    return LABEL_TO_CATEGORY.get(label.strip().lower().replace(" ", "_").replace("-", "_"))


def availability() -> tuple[bool, str]:
    if importlib.util.find_spec("ultralytics") is None:
        return False, "ultralytics is not installed (pip install -r requirements-ai.txt)"
    if not MODEL_PATH.exists():
        return False, f"trained model not found at {MODEL_PATH}"
    return True, "ready"


_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    ok, reason = availability()
    if not ok:
        raise DetectorUnavailable(reason)
    with _lock:
        if _model is None:
            from ultralytics import YOLO
            _model = YOLO(str(MODEL_PATH))
    return _model


def detect_category(image_bytes: bytes) -> Detection | None:
    """Return the most confident known civic issue in the photo, or None."""
    model = _get_model()
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    with _lock:  # one inference at a time; keeps CPU use predictable
        result = model.predict(source=image, conf=MIN_CONFIDENCE, verbose=False)[0]

    best: Detection | None = None
    for cls_id, conf in zip(result.boxes.cls.tolist(), result.boxes.conf.tolist()):
        category = map_label(str(result.names[int(cls_id)]))
        if category and (best is None or conf > best.confidence):
            best = Detection(category, float(conf))
    return best
