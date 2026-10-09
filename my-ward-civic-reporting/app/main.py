import secrets
import uuid
from contextlib import asynccontextmanager

from fastapi import (
    Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from . import config
from . import detector
from .database import Base, engine, ensure_columns, get_db
from .detector import DetectorUnavailable, detect_category
from .enums import Category, Priority, Status
from .images import detect_image_type
from .models import Complaint, StatusHistory
from .routing import route_complaint, ward_from_coordinates
from .schemas import ComplaintOut, Stats, StatusUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    ensure_columns()
    yield


app = FastAPI(
    title="My Ward - Civic Issue Reporting",
    description="Citizens report civic issues; complaints are routed to departments.",
    version="1.0.0",
    lifespan=lifespan,
)

# Uploaded photos are served from /uploads/<filename>
config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(config.UPLOAD_DIR)), name="uploads")


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    """Protects dashboard endpoints when MYWARD_ADMIN_KEY is set."""
    if not config.ADMIN_KEY:
        return
    supplied = (x_admin_key or "").encode()
    if not secrets.compare_digest(supplied, config.ADMIN_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key header.")


@app.get("/", tags=["health"])
def root():
    ai_ready, ai_note = detector.availability()
    return {
        "app": "My Ward",
        "status": "running",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "ai_detection": {"ready": ai_ready, "note": ai_note},
    }


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(config.STATIC_DIR / "dashboard.html")


@app.post("/complaints", response_model=ComplaintOut, status_code=201, tags=["complaints"])
async def create_complaint(
    citizen_name: str = Form(..., min_length=1, max_length=100),
    category: Category | None = Form(default=None),
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    description: str | None = Form(default=None, max_length=2000),
    image: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    image_bytes = None
    ext = None
    if image is not None and image.filename:
        image_bytes = await image.read(config.MAX_IMAGE_BYTES + 1)
        if len(image_bytes) > config.MAX_IMAGE_BYTES:
            raise HTTPException(413, "Image too large (max 5 MB).")
        ext = detect_image_type(image_bytes)
        if ext is None:
            raise HTTPException(400, "Image must be a valid JPG, PNG or WEBP file.")

    # Category: citizen's choice wins; otherwise detect it from the photo.
    category_source = "citizen"
    ai_confidence = None
    if category is None:
        if image_bytes is None:
            raise HTTPException(
                422, "Choose a category, or upload a photo so the issue can be detected automatically."
            )
        try:
            detection = await run_in_threadpool(detect_category, image_bytes)
        except DetectorUnavailable as exc:
            raise HTTPException(422, f"Automatic detection is not available ({exc}). Please choose a category.")
        if detection is None:
            raise HTTPException(422, "No known civic issue was recognised in the photo. Please choose a category.")
        category = detection.category
        category_source = "ai"
        ai_confidence = round(detection.confidence, 3)

    saved_filename = None
    if image_bytes is not None:
        saved_filename = f"{uuid.uuid4().hex}.{ext}"
        (config.UPLOAD_DIR / saved_filename).write_bytes(image_bytes)

    department, priority = route_complaint(category)
    complaint = Complaint(
        citizen_name=citizen_name.strip(),
        category=category.value,
        category_source=category_source,
        ai_confidence=ai_confidence,
        description=description.strip() if description else None,
        latitude=latitude,
        longitude=longitude,
        ward_number=ward_from_coordinates(latitude, longitude),
        department=department,
        priority=priority.value,
        status=Status.SUBMITTED.value,
        image_filename=saved_filename,
    )
    complaint.history.append(StatusHistory(status=Status.SUBMITTED.value, note="Complaint submitted"))

    try:
        db.add(complaint)
        db.commit()
    except Exception:
        db.rollback()
        if saved_filename:
            (config.UPLOAD_DIR / saved_filename).unlink(missing_ok=True)
        raise
    db.refresh(complaint)
    return complaint


@app.get(
    "/complaints",
    response_model=list[ComplaintOut],
    dependencies=[Depends(require_admin)],
    tags=["dashboard"],
)
def list_complaints(
    status: Status | None = None,
    category: Category | None = None,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = (
        select(Complaint)
        .options(selectinload(Complaint.history))
        .order_by(Complaint.id.desc())
        .limit(limit)
    )
    if status:
        query = query.where(Complaint.status == status.value)
    if category:
        query = query.where(Complaint.category == category.value)
    return db.scalars(query).all()


@app.get("/complaints/{complaint_id}", response_model=ComplaintOut, tags=["complaints"])
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(404, "Complaint not found.")
    return complaint


@app.patch(
    "/complaints/{complaint_id}/status",
    response_model=ComplaintOut,
    dependencies=[Depends(require_admin)],
    tags=["dashboard"],
)
def update_status(complaint_id: int, body: StatusUpdate, db: Session = Depends(get_db)):
    complaint = db.get(Complaint, complaint_id)
    if complaint is None:
        raise HTTPException(404, "Complaint not found.")
    if complaint.status == body.status.value:
        raise HTTPException(400, f"Complaint is already '{body.status.value}'.")
    complaint.status = body.status.value
    complaint.history.append(StatusHistory(status=body.status.value, note=body.note))
    db.commit()
    db.refresh(complaint)
    return complaint


@app.get("/stats", response_model=Stats, dependencies=[Depends(require_admin)], tags=["dashboard"])
def stats(db: Session = Depends(get_db)):
    def count(condition=None) -> int:
        query = select(func.count(Complaint.id))
        if condition is not None:
            query = query.where(condition)
        return db.scalar(query) or 0

    return Stats(
        total=count(),
        submitted=count(Complaint.status == Status.SUBMITTED.value),
        in_progress=count(Complaint.status == Status.IN_PROGRESS.value),
        resolved=count(Complaint.status == Status.RESOLVED.value),
        high_priority=count(Complaint.priority == Priority.HIGH.value),
    )
