from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from app.schemas.auth import UserLoginRequest, UserRegisterRequest
from app.schemas.task import TaskCreateRequest, TaskUpdateRequest


@pytest.mark.unit
def test_user_register_trims_full_name():
    req = UserRegisterRequest(
        email="p.zielinski@student.edu.pl",
        password="HasloStudenta123!",
        full_name="  Piotr Zieliński  ",
        role="student",
    )
    assert req.full_name == "Piotr Zieliński"


@pytest.mark.unit
def test_user_register_rejects_whitespace_full_name():
    with pytest.raises(ValidationError):
        UserRegisterRequest(
            email="p.zielinski@student.edu.pl",
            password="HasloStudenta123!",
            full_name="    ",
            role="student",
        )


@pytest.mark.unit
def test_user_register_rejects_padded_single_char_full_name():
    with pytest.raises(ValidationError):
        UserRegisterRequest(
            email="p.zielinski@student.edu.pl",
            password="HasloStudenta123!",
            full_name=" a ",
            role="student",
        )


@pytest.mark.unit
def test_user_login_rejects_whitespace_password():
    with pytest.raises(ValidationError):
        UserLoginRequest(
            email="p.zielinski@student.edu.pl",
            password="   ",
        )


@pytest.mark.unit
def test_task_create_accepts_valid_trimmed_fields():
    future = datetime.now(timezone.utc) + timedelta(days=3)
    req = TaskCreateRequest(
        title="  Projekt końcowy  ",
        description="  Opis wymagań  ",
        deadline=future,
    )
    assert req.title == "Projekt końcowy"
    assert req.description == "Opis wymagań"


@pytest.mark.unit
def test_task_create_rejects_padded_short_title():
    future = datetime.now(timezone.utc) + timedelta(days=3)
    with pytest.raises(ValidationError):
        TaskCreateRequest(
            title="  ab  ",
            description="Opis",
            deadline=future,
        )


@pytest.mark.unit
def test_task_update_rejects_whitespace_title():
    with pytest.raises(ValidationError):
        TaskUpdateRequest(title="   ")
