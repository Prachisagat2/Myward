"""Train a YOLOv8 model on your civic-issue dataset and install it for the API.

Usage:
    pip install -r requirements-ai.txt
    python scripts/train.py --data datasets/civic/data.yaml --epochs 50

The dataset must be in YOLO format (images + labels + data.yaml). Class names in
data.yaml should be e.g. pothole, garbage, streetlight (see app/detector.py for
accepted aliases).
"""
import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="path to data.yaml")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--base", default="yolov8n.pt", help="starting weights")
    args = parser.parse_args()

    model = YOLO(args.base)
    results = model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, project=str(ROOT / "runs"))
    best = Path(results.save_dir) / "weights" / "best.pt"
    target = ROOT / "models" / "best.pt"
    target.parent.mkdir(exist_ok=True)
    shutil.copy(best, target)
    print(f"Model installed at {target}. Restart the server to use it.")


if __name__ == "__main__":
    main()
