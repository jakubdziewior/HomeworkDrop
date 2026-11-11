from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status


def _normalize_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.astimezone()
    return dt


def is_deadline_passed(deadline: datetime, current_time: Optional[datetime] = None) -> bool:
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    return _normalize_dt(current_time) > _normalize_dt(deadline)


def validate_submission_deadline(deadline: datetime, current_time: Optional[datetime] = None) -> None:
    if is_deadline_passed(deadline, current_time):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Termin przesyłania rozwiązań dla tego zadania upłynął (blokada deadline)."
        )
