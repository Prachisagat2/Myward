import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"

DATABASE_URL = os.getenv("MYWARD_DATABASE_URL", f"sqlite:///{BASE_DIR / 'myward.db'}")
UPLOAD_DIR = Path(os.getenv("MYWARD_UPLOAD_DIR", str(BASE_DIR / "uploads")))

# If set, the dashboard API (list, stats, status update) requires the header
# X-Admin-Key: <value>. If empty, those endpoints are open (demo mode).
ADMIN_KEY = os.getenv("MYWARD_ADMIN_KEY", "")

MAX_IMAGE_BYTES = 5 * 1024 * 1024
