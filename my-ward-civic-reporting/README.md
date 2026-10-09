# My Ward - Civic Issue Reporting

Citizens report civic problems (potholes, garbage, broken streetlights...) with an optional
photo and GPS location. Each complaint is automatically routed to the right department and
tracked through a status history. Authorities manage everything from a live dashboard.

**Stack:** FastAPI, SQLAlchemy 2, SQLite, plain HTML/JS dashboard. Requires Python 3.10+.

## Quick start

```bash
# Windows
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

| URL | Purpose |
|---|---|
| http://127.0.0.1:8000/ | Health check |
| http://127.0.0.1:8000/docs | Swagger UI - submit and test complaints |
| http://127.0.0.1:8000/dashboard | Authority dashboard (auto-refreshes every 10 s) |

The SQLite file `myward.db` and the `uploads/` folder are created automatically.

## Try it

In Swagger (`/docs`) open `POST /complaints` > **Try it out** and submit:

| Field | Value |
|---|---|
| citizen_name | Rahul Patil |
| category | pothole (leave empty to use AI detection, needs a photo) |
| latitude | 18.6298 |
| longitude | 73.7997 |
| description | Large pothole near market road |
| image | optional JPG / PNG / WEBP, max 5 MB |

Result: department **Road Maintenance Department**, priority **High**, status **Submitted**,
plus an auto-generated ward number. Then open `/dashboard`.

Or with curl:

```bash
curl -X POST http://127.0.0.1:8000/complaints \
  -F citizen_name="Rahul Patil" -F category=pothole \
  -F latitude=18.6298 -F longitude=73.7997 \
  -F description="Large pothole near market road" \
  -F image=@photo.jpg
```

## Routing

| Category | Department | Priority |
|---|---|---|
| pothole | Road Maintenance Department | High |
| garbage | Solid Waste Management Department | Medium |
| streetlight | Electrical Department | Medium |
| water_leakage | Water Supply Department | High |
| drainage | Drainage and Sewerage Department | High |
| illegal_dumping | Sanitation Enforcement Department | Medium |

Edit `app/routing.py` to change departments or priorities.

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/complaints` | public | Submit a complaint (multipart form) |
| GET | `/complaints/{id}` | public | Track one complaint with its history |
| GET | `/complaints` | admin* | List complaints (`?status=`, `?category=`, `?limit=`) |
| PATCH | `/complaints/{id}/status` | admin* | Change status, e.g. `{"status": "In Progress", "note": "Crew sent"}` |
| GET | `/stats` | admin* | Dashboard counters |

Statuses: Submitted, Verified, Assigned, In Progress, Resolved, Reopened, Rejected.
Every change is stored in the complaint's history.

## AI detection (YOLOv8) - optional

If you leave `category` empty and upload a photo, a YOLOv8 model detects the issue and fills in the
category (the dashboard shows "AI 87%"). A category chosen by the citizen always wins.

1. Install the extras: `python -m pip install -r requirements-ai.txt`
2. Get a YOLO-format dataset (pothole, garbage, streetlight... from Roboflow or Kaggle) with a `data.yaml`.
3. Train: `python scripts/train.py --data datasets/civic/data.yaml --epochs 50`
   (this copies the result to `models/best.pt`; use a GPU or Google Colab for speed)
4. Restart the server. `GET /` shows `"ai_detection": {"ready": true}` when the model is loaded.

Class names in your dataset are matched through `LABEL_TO_CATEGORY` in `app/detector.py`; add aliases
there if your labels differ. Without the model, everything else still works and photo-only
submissions return a clear 422 asking for a category. Tune the threshold with `MYWARD_MIN_CONFIDENCE`
(default 0.4) and the model location with `MYWARD_MODEL_PATH`.

## Securing the dashboard

By default the dashboard API is **open** (demo mode). To require a key, set an environment variable
before starting the server:

```bash
# Linux / macOS
export MYWARD_ADMIN_KEY="choose-a-long-random-string"
# Windows (PowerShell)
$env:MYWARD_ADMIN_KEY="choose-a-long-random-string"
```

The dashboard page then asks for the key (stored in `sessionStorage` for that tab only). This is a
shared-secret stopgap; use real per-user login before any public deployment, and serve over HTTPS.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `MYWARD_DATABASE_URL` | `sqlite:///./myward.db` | SQLAlchemy URL |
| `MYWARD_UPLOAD_DIR` | `./uploads` | Where photos are stored |
| `MYWARD_ADMIN_KEY` | empty (open) | Protects dashboard endpoints |
| `MYWARD_MODEL_PATH` | `./models/best.pt` | Trained YOLO weights |
| `MYWARD_MIN_CONFIDENCE` | `0.4` | Minimum detection confidence |

## Tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

GitHub Actions runs the same tests on every push (`.github/workflows/ci.yml`).

## Known limitations / next steps

- **Ward number is a placeholder** (grid-based, `ward_from_coordinates` in `app/routing.py`).
  Replace it with a point-in-polygon lookup against your city's ward boundary GeoJSON.
- The YOLO integration is written but needs a model you train yourself; no pretrained civic model is included.
- Photos are stored on local disk; move to Cloudinary/S3 for deployment.
- No schema migrations (tables are created on startup). Add Alembic if the schema will change.
- Later: Android client (CameraX, GPS, Room), Deep SORT for video.
