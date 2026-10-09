from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    # Stored as naive UTC; the API/dashboard treat it as UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    citizen_name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(30), index=True)
    category_source: Mapped[str] = mapped_column(String(10), default="citizen", server_default="citizen")
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    ward_number: Mapped[int] = mapped_column(Integer, index=True)
    department: Mapped[str] = mapped_column(String(100))
    priority: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    image_filename: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    history: Mapped[list["StatusHistory"]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="StatusHistory.id",
    )

    @property
    def image_url(self) -> str | None:
        return f"/uploads/{self.image_filename}" if self.image_filename else None


class StatusHistory(Base):
    __tablename__ = "status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    complaint: Mapped[Complaint] = relationship(back_populates="history")
