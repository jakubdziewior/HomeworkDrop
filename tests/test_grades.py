from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import Submission

STUDENT = {"email": "p.zielinski@student.edu.pl", "password": "HasloStudenta123!",
           "full_name": "Piotr Zieliński", "role": "student"}
OTHER_STUDENT = {"email": "k.lewandowska@student.edu.pl", "password": "HasloStudentki123!",
                 "full_name": "Katarzyna Lewandowska", "role": "student"}
TEACHER = {"email": "t.kaminski@uczelnia.edu.pl", "password": "HasloProwadzacego123!",
           "full_name": "dr Tomasz Kamiński", "role": "teacher"}
OTHER_TEACHER = {"email": "a.nowak@uczelnia.edu.pl", "password": "InneHaslo123!",
                 "full_name": "dr Anna Nowak", "role": "teacher"}

PDF = b"%PDF-1.7\n%%EOF\n"


def _logged_in(user: dict) -> TestClient:
    c = TestClient(app, base_url="https://testserver")
    assert c.post("/api/v1/auth/register", json=user).status_code == 201
    res = c.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})
    assert res.status_code == 200
    return c


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    yield


@pytest.fixture
def teacher():
    return _logged_in(TEACHER)


@pytest.fixture
def student():
    return _logged_in(STUDENT)


@pytest.fixture
def task_id(teacher):
    res = teacher.post("/api/v1/tasks", json={
        "title": "Analiza podatności",
        "deadline": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
    })
    assert res.status_code == 201
    return res.json()["id"]


def _upload(client, task_id, data=None):
    return client.post(
        f"/api/v1/tasks/{task_id}/submissions",
        files={"file": ("raport.pdf", PDF, "application/pdf")},
        data=data,
    )


@pytest.fixture
def submission_id(student, task_id):
    res = _upload(student, task_id)
    assert res.status_code == 201
    return res.json()["id"]


def _snapshot(db, sub_id: int) -> dict:
    db.expire_all()
    sub = db.get(Submission, sub_id)
    return {c.name: getattr(sub, c.name) for c in Submission.__table__.columns}


def _grade_url(sub_id: int) -> str:
    return f"/api/v1/submissions/{sub_id}/grade"


# --- Wystawianie oceny ---------------------------------------------------

def test_teacher_grades_submission(teacher, submission_id):
    res = teacher.put(_grade_url(submission_id), json={"grade": 4.5, "feedback": "  Dobra robota.  "})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["grade"] == 4.5
    assert body["feedback"] == "Dobra robota."
    assert body["status"] == "graded"
    assert body["graded_by"] == 1
    assert body["graded_at"] is not None


def test_teacher_can_change_grade(teacher, submission_id):
    teacher.put(_grade_url(submission_id), json={"grade": 3.0})
    res = teacher.put(_grade_url(submission_id), json={"grade": 5.0, "feedback": "Po poprawie."})
    assert res.status_code == 200
    assert res.json()["grade"] == 5.0


def test_student_sees_grade_in_own_submission(teacher, student, task_id, submission_id):
    teacher.put(_grade_url(submission_id), json={"grade": 4.0, "feedback": "OK"})
    body = student.get(f"/api/v1/tasks/{task_id}/submissions/me").json()
    assert body["grade"] == 4.0
    assert body["feedback"] == "OK"
    assert body["status"] == "graded"


def test_new_submission_is_ungraded(student, task_id, submission_id):
    body = student.get(f"/api/v1/tasks/{task_id}/submissions/me").json()
    assert body["status"] == "submitted"
    assert body["grade"] is None


# --- Walidacja wartości --------------------------------------------------

@pytest.mark.parametrize("grade", [2, 3.0, 3.5, 4, 4.5, 5])
def test_allowed_grade_scale(teacher, submission_id, grade):
    assert teacher.put(_grade_url(submission_id), json={"grade": grade}).status_code == 200


@pytest.mark.parametrize("grade", [6.0, 1.0, 0, -5, 2.5, 4.75, 100, "5.0", True, None, [5.0]])
def test_invalid_grades_rejected(teacher, submission_id, grade, db):
    res = teacher.put(_grade_url(submission_id), json={"grade": grade})
    assert res.status_code == 422
    assert _snapshot(db, submission_id)['grade'] is None


def test_missing_grade_rejected(teacher, submission_id):
    assert teacher.put(_grade_url(submission_id), json={"feedback": "Brak oceny"}).status_code == 422


def test_feedback_too_long_rejected(teacher, submission_id):
    res = teacher.put(_grade_url(submission_id), json={"grade": 5.0, "feedback": "x" * 2001})
    assert res.status_code == 422


# --- Mass Assignment przy ocenianiu --------------------------------------

@pytest.mark.parametrize("extra", [
    {"graded_by": 999},
    {"student_id": 2},
    {"task_id": 2},
    {"status": "submitted"},
    {"graded_at": "2020-01-01T00:00:00Z"},
    {"original_filename": "podmiana.pdf"},
    {"id": 50},
])
def test_grade_request_rejects_extra_fields(teacher, submission_id, extra, db):
    before = _snapshot(db, submission_id)
    res = teacher.put(_grade_url(submission_id), json={"grade": 5.0, **extra})
    assert res.status_code == 422
    assert _snapshot(db, submission_id) == before


# --- RBAC / IDOR ---------------------------------------------------------

def test_student_cannot_grade_own_submission(student, submission_id, db):
    res = student.put(_grade_url(submission_id), json={"grade": 5.0})
    assert res.status_code == 403
    assert _snapshot(db, submission_id)['grade'] is None


def test_other_teacher_cannot_grade(submission_id, db):
    other = _logged_in(OTHER_TEACHER)
    res = other.put(_grade_url(submission_id), json={"grade": 2.0})
    assert res.status_code == 404
    assert _snapshot(db, submission_id)['grade'] is None


def test_anonymous_cannot_grade(submission_id):
    anon = TestClient(app, base_url="https://testserver")
    assert anon.put(_grade_url(submission_id), json={"grade": 5.0}).status_code == 401


def test_grade_nonexistent_submission(teacher):
    assert teacher.put(_grade_url(999), json={"grade": 5.0}).status_code == 404


# --- Mass Assignment po stronie studenta ---------------------------------

@pytest.mark.parametrize("extra", [
    {"grade": "5.0"},
    {"feedback": "Świetna praca"},
    {"status": "graded"},
    {"student_id": "2"},
])
def test_student_upload_rejects_extra_form_fields(student, task_id, extra, db):
    res = _upload(student, task_id, data=extra)
    assert res.status_code == 422
    assert db.query(Submission).count() == 0


def test_student_reupload_with_grade_field_does_not_change_grade(teacher, student, task_id, submission_id, db):
    teacher.put(_grade_url(submission_id), json={"grade": 3.0})
    res = _upload(student, task_id, data={"grade": "5.0"})
    assert res.status_code == 422
    assert _snapshot(db, submission_id)['grade'] == 3.0


def test_student_cannot_replace_file_after_grading(teacher, student, task_id, submission_id, db):
    teacher.put(_grade_url(submission_id), json={"grade": 4.0})
    before = _snapshot(db, submission_id)
    res = _upload(student, task_id)
    assert res.status_code == 409
    assert _snapshot(db, submission_id) == before


def test_reupload_before_grading_keeps_submission_ungraded(student, task_id, submission_id):
    res = _upload(student, task_id)
    assert res.status_code == 200
    assert res.json()["status"] == "submitted"
    assert res.json()["grade"] is None
