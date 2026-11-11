from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException
from app.services.deadline_service import is_deadline_passed, validate_submission_deadline


def test_deadline_in_future():
    future_deadline = datetime.now(timezone.utc) + timedelta(days=2)
    assert is_deadline_passed(future_deadline) is False
    validate_submission_deadline(future_deadline)


def test_deadline_in_past_raises_400():
    past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
    assert is_deadline_passed(past_deadline) is True

    with pytest.raises(HTTPException) as exc_info:
        validate_submission_deadline(past_deadline)

    assert exc_info.value.status_code == 400
    assert "upłynął" in exc_info.value.detail
    assert "blokada deadline" in exc_info.value.detail


def test_deadline_timezone_compatibility():
    now_utc = datetime.now(timezone.utc)
    past = now_utc - timedelta(minutes=10)
    future = now_utc + timedelta(minutes=10)

    assert is_deadline_passed(past, now_utc) is True
    assert is_deadline_passed(future, now_utc) is False


def test_deadline_exact_match():
    reference_time = datetime(2026, 11, 11, 12, 0, 0, tzinfo=timezone.utc)
    just_before = reference_time - timedelta(seconds=1)
    just_after = reference_time + timedelta(seconds=1)

    assert is_deadline_passed(reference_time, just_before) is False
    assert is_deadline_passed(reference_time, just_after) is True
