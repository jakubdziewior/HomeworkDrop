"""
Testy jednostkowe schematu GradeRequest (app/schemas/submission.py):
skala ocen, brak niejawnej konwersji typów, komentarz i odrzucanie nadmiarowych pól.
"""

import math
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models import Submission
from app.schemas.submission import ALLOWED_GRADES, GradeRequest


def _errors(payload: dict) -> list[dict]:
    with pytest.raises(ValidationError) as exc:
        GradeRequest.model_validate(payload)
    return exc.value.errors()


# --- Skala ---------------------------------------------------------------

def test_scale_is_the_university_scale():
    assert ALLOWED_GRADES == (2.0, 3.0, 3.5, 4.0, 4.5, 5.0)


def test_api_scale_matches_database_check_constraint():
    check = next(c for c in Submission.__table__.constraints if str(c.name).endswith("grade_scale"))
    sql = str(check.sqltext)
    for value in ALLOWED_GRADES:
        assert str(value) in sql
    assert "2.5" not in sql and "1.0" not in sql


@pytest.mark.parametrize("value", [2, 2.0, 3, 3.0, 3.5, 4, 4.0, 4.5, 5, 5.0])
def test_allowed_values_accepted_and_normalized_to_float(value):
    req = GradeRequest(grade=value)
    assert req.grade == float(value)
    assert type(req.grade) is float


@pytest.mark.parametrize("value", [
    0, 1, 1.0, 2.5, 2.9999, 3.25, 3.75, 4.25, 4.75, 5.5, 6, 6.0, 10, 100, -2, -5.0,
    4.000001, 1e308, -0.0,
])
def test_values_outside_scale_rejected(value):
    errors = _errors({"grade": value})
    assert errors[0]["loc"] == ("grade",)
    assert "Niedozwolona ocena" in errors[0]["msg"]


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_special_floats_rejected(value):
    assert _errors({"grade": value})[0]["loc"] == ("grade",)


@pytest.mark.parametrize("value", [
    "5", "5.0", "4,5", " 4.0 ", "", "piątka", True, False, None, [5.0], {"value": 5.0}, Decimal("5.0"), b"5",
])
def test_non_numeric_types_rejected_without_coercion(value):
    errors = _errors({"grade": value})
    assert errors[0]["loc"] == ("grade",)
    assert "liczbą" in errors[0]["msg"]


def test_grade_is_required():
    assert _errors({"feedback": "Brak oceny"})[0]["type"] == "missing"


def test_grade_validation_from_json_string():
    assert GradeRequest.model_validate_json('{"grade": 4.5}').grade == 4.5
    with pytest.raises(ValidationError):
        GradeRequest.model_validate_json('{"grade": "4.5"}')


# --- Komentarz -------------------------------------------------------------

def test_feedback_defaults_to_empty_string():
    assert GradeRequest(grade=5.0).feedback == ""


def test_feedback_is_stripped():
    assert GradeRequest(grade=5.0, feedback="  \n Dobra robota.\t ").feedback == "Dobra robota."


def test_feedback_max_length_boundary():
    assert len(GradeRequest(grade=5.0, feedback="x" * 2000).feedback) == 2000
    assert _errors({"grade": 5.0, "feedback": "x" * 2001})[0]["type"] == "string_too_long"


def test_feedback_keeps_markup_as_plain_text():
    # Schemat nie modyfikuje treści – escapowanie należy do warstwy prezentacji (React).
    text = "<b>uwaga</b> & \"cytat\""
    assert GradeRequest(grade=3.0, feedback=text).feedback == text


@pytest.mark.parametrize("value", [None, 5, ["a"]])
def test_feedback_must_be_string(value):
    assert _errors({"grade": 5.0, "feedback": value})[0]["loc"] == ("feedback",)


# --- Mass Assignment na poziomie schematu ----------------------------------

@pytest.mark.parametrize("field,value", [
    ("graded_by", 1), ("graded_at", "2020-01-01T00:00:00Z"), ("status", "graded"),
    ("student_id", 2), ("task_id", 3), ("id", 1), ("sha256", "0" * 64), ("Grade", 5.0),
])
def test_extra_fields_forbidden(field, value):
    errors = _errors({"grade": 5.0, field: value})
    assert errors[0]["type"] == "extra_forbidden"
    assert errors[0]["loc"] == (field,)


def test_model_dump_contains_only_grade_and_feedback():
    assert set(GradeRequest(grade=4.0, feedback="ok").model_dump()) == {"grade", "feedback"}
