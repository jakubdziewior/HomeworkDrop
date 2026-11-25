from datetime import datetime, timedelta, timezone
import pytest
from fastapi import HTTPException

from app.services.deadline_service import is_deadline_passed, validate_submission_deadline


@pytest.mark.unit
def test_is_deadline_passed_returns_false_for_future():
    future_deadline = datetime.now(timezone.utc) + timedelta(days=2)
    assert is_deadline_passed(future_deadline) is False


@pytest.mark.unit
def test_is_deadline_passed_returns_true_for_past():
    past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
    assert is_deadline_passed(past_deadline) is True


@pytest.mark.unit
def test_validate_submission_deadline_allows_future():
    future_deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
    validate_submission_deadline(future_deadline)


@pytest.mark.unit
def test_validate_submission_deadline_raises_400_for_past():
    past_deadline = datetime.now(timezone.utc) - timedelta(seconds=5)
    with pytest.raises(HTTPException) as exc_info:
        validate_submission_deadline(past_deadline)

    assert exc_info.value.status_code == 400
    assert "upłynął" in exc_info.value.detail
    assert "blokada deadline" in exc_info.value.detail


@pytest.mark.unit
def test_is_deadline_passed_allows_exact_boundary():
    reference_time = datetime(2026, 11, 11, 12, 0, 0, tzinfo=timezone.utc)
    assert is_deadline_passed(reference_time, reference_time) is False


@pytest.mark.unit
def test_is_deadline_passed_blocks_one_second_after():
    reference_time = datetime(2026, 11, 11, 12, 0, 0, tzinfo=timezone.utc)
    one_second_after = reference_time + timedelta(seconds=1)
    assert is_deadline_passed(reference_time, one_second_after) is True


@pytest.mark.unit
def test_is_deadline_passed_normalizes_timezone_offsets():
    deadline_utc = datetime(2026, 11, 11, 12, 0, 0, tzinfo=timezone.utc)
    cet = timezone(timedelta(hours=1))
    before_in_cet = datetime(2026, 11, 11, 12, 59, 0, tzinfo=cet)
    after_in_cet = datetime(2026, 11, 11, 13, 1, 0, tzinfo=cet)

    assert is_deadline_passed(deadline_utc, before_in_cet) is False
    assert is_deadline_passed(deadline_utc, after_in_cet) is True
