from datetime import datetime, timezone
from typing import Optional

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


def _strip_required(v: str, field_label: str) -> str:
    trimmed = v.strip()
    if not trimmed:
        raise ValueError(f"{field_label} nie może być pusty.")
    return trimmed


def _ensure_future(v: datetime) -> datetime:
    v = v.astimezone(timezone.utc)
    if v <= datetime.now(timezone.utc):
        raise ValueError("Termin oddania musi być datą w przyszłości.")
    return v


class TaskCreateRequest(BaseModel):
    # extra="forbid" – ochrona przed Mass Assignment (np. podmianą created_by / id).
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field("", max_length=5000)
    deadline: AwareDatetime

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        return _strip_required(v, "Tytuł")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        return v.strip()

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, v: datetime) -> datetime:
        return _ensure_future(v)


class TaskUpdateRequest(BaseModel):
    """Częściowa aktualizacja (PATCH) – przesyłane są tylko zmieniane pola."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    deadline: Optional[AwareDatetime] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> str:
        if v is None:
            raise ValueError("Tytuł nie może być pusty.")
        return _strip_required(v, "Tytuł")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> str:
        return "" if v is None else v.strip()

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, v: Optional[datetime]) -> datetime:
        if v is None:
            raise ValueError("Termin oddania nie może być pusty.")
        return _ensure_future(v)


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    deadline: datetime
    created_by: int
    created_at: datetime
    updated_at: datetime
    is_expired: bool
