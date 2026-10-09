from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .enums import Status


class StatusHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    note: str | None
    changed_at: datetime


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    citizen_name: str
    category: str
    category_source: str
    ai_confidence: float | None
    description: str | None
    latitude: float
    longitude: float
    ward_number: int
    department: str
    priority: str
    status: str
    image_url: str | None
    created_at: datetime
    updated_at: datetime
    history: list[StatusHistoryOut]


class StatusUpdate(BaseModel):
    status: Status
    note: str | None = Field(default=None, max_length=500)


class Stats(BaseModel):
    total: int
    submitted: int
    in_progress: int
    resolved: int
    high_priority: int
