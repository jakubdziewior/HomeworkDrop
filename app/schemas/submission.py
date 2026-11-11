from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Skala ocen stosowana na uczelni.
ALLOWED_GRADES = (2.0, 3.0, 3.5, 4.0, 4.5, 5.0)


class GradeRequest(BaseModel):
    """
    Jedyne pola, które prowadzący może ustawić przy ocenianiu.
    extra="forbid" – ochrona przed Mass Assignment: pola takie jak graded_by,
    student_id, task_id czy status są odrzucane (422), a nie po cichu ignorowane.
    """

    model_config = ConfigDict(extra="forbid")

    grade: float = Field(..., description=f"Ocena z dozwolonej skali: {', '.join(map(str, ALLOWED_GRADES))}")
    feedback: str = Field("", max_length=2000, description="Komentarz zwrotny dla studenta")

    @field_validator("grade", mode="before")
    @classmethod
    def validate_grade_type(cls, v: Any) -> Any:
        # Bez niejawnej konwersji: "5.0" (tekst) ani true/false nie są ocenami.
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("Ocena musi być liczbą.")
        return v

    @field_validator("grade")
    @classmethod
    def validate_grade_scale(cls, v: float) -> float:
        if v not in ALLOWED_GRADES:
            raise ValueError(f"Niedozwolona ocena. Dozwolone wartości: {', '.join(map(str, ALLOWED_GRADES))}.")
        return float(v)

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v: str) -> str:
        return v.strip()


class SubmissionResponse(BaseModel):
    """Publiczny widok zgłoszenia – bez nazwy pliku na dysku ani ścieżek serwera."""

    id: int
    task_id: int
    student_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    submitted_at: datetime
    updated_at: datetime
    status: Literal["submitted", "graded"] = "submitted"
    grade: Optional[float] = None
    feedback: Optional[str] = None
    graded_by: Optional[int] = None
    graded_at: Optional[datetime] = None
