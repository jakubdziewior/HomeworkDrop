"""
Scenariusze Mass Assignment / nadmiernej ekspozycji danych: próby samodzielnego
ustawienia oceny przez studenta, podmiany właściciela zasobów i eskalacji roli.
"""

import pytest

from app.models import Submission, Task, User
from tests.helpers import (
    OTHER_TEACHER, PDF, STUDENT, TEACHER, anonymous, create_task, future, grade, logged_in, login, upload,
)


@pytest.fixture
def teacher():
    return logged_in(TEACHER)


@pytest.fixture
def student():
    return logged_in(STUDENT)


@pytest.fixture
def task_id(teacher):
    return create_task(teacher)


@pytest.fixture
def submission_id(student, task_id):
    return upload(student, task_id).json()["id"]


def _row(db, sub_id):
    db.expire_all()
    s = db.get(Submission, sub_id)
    return {c.name: getattr(s, c.name) for c in Submission.__table__.columns}


# --- Student próbuje wystawić sobie ocenę ---------------------------------------

@pytest.mark.parametrize("body", [
    {"grade": 5.0},
    {"grade": 5.0, "feedback": "Świetnie"},
    {"grade": 5.0, "role": "teacher"},
    {"grade": 5.0, "graded_by": 1},
])
def test_student_cannot_grade_via_grade_endpoint(student, submission_id, db, body):
    before = _row(db, submission_id)
    assert grade(student, submission_id, body).status_code == 403
    assert _row(db, submission_id) == before


@pytest.mark.parametrize("field,value", [
    ("grade", "5.0"), ("status", "graded"), ("feedback", "Sam sobie"), ("graded_by", "1"),
    ("graded_at", "2020-01-01"), ("student_id", "99"), ("task_id", "2"), ("sha256", "0" * 64),
    ("stored_filename", "../../app/main.py"), ("id", "1"),
])
def test_upload_form_rejects_injected_fields(student, task_id, db, field, value):
    res = upload(student, task_id, data={field: value})
    assert res.status_code == 422
    assert field in res.json()["detail"]
    assert db.query(Submission).count() == 0


def test_upload_query_params_cannot_set_grade(student, task_id, db):
    res = upload(student, task_id, params={"grade": "5.0", "status": "graded", "student_id": "99"})
    assert res.status_code == 201
    row = _row(db, res.json()["id"])
    assert (row["grade"], row["status"], row["student_id"]) == (None, "submitted", res.json()["student_id"])


def test_two_file_fields_do_not_bypass_whitelist(student, task_id):
    res = student.post(
        f"/api/v1/tasks/{task_id}/submissions",
        files=[("file", ("a.pdf", PDF, "application/pdf")), ("grade", ("g.txt", b"5.0", "text/plain"))],
    )
    assert res.status_code == 422


def test_grade_endpoint_rejects_form_encoded_body(teacher, submission_id, db):
    res = teacher.put(f"/api/v1/submissions/{submission_id}/grade", data={"grade": "5.0"})
    assert res.status_code == 422
    assert _row(db, submission_id)["grade"] is None


def test_grade_endpoint_rejects_non_object_json(teacher, submission_id):
    for body in ([{"grade": 5.0}], "5.0", 5.0, None):
        assert teacher.put(f"/api/v1/submissions/{submission_id}/grade", json=body).status_code == 422


def test_teacher_cannot_reassign_submission_via_grade(teacher, submission_id, db):
    other_id = logged_in(OTHER_TEACHER).get("/api/v1/auth/me").json()["id"]
    before = _row(db, submission_id)
    res = grade(teacher, submission_id, {"grade": 4.0, "graded_by": other_id, "student_id": 999})
    assert res.status_code == 422
    assert _row(db, submission_id) == before


def test_server_sets_graded_fields_regardless_of_client(teacher, submission_id, db):
    me = teacher.get("/api/v1/auth/me").json()["id"]
    res = grade(teacher, submission_id, {"grade": 3.5})
    assert res.status_code == 200
    row = _row(db, submission_id)
    assert row["graded_by"] == me
    assert row["status"] == "graded"
    assert row["graded_at"] is not None


# --- Zadania: podmiana autora / flag ------------------------------------------

@pytest.mark.parametrize("extra", [
    {"created_by": 2}, {"id": 77}, {"is_expired": True}, {"created_at": "2020-01-01T00:00:00Z"},
    {"updated_at": "2020-01-01T00:00:00Z"}, {"submissions": []},
])
def test_task_create_rejects_server_fields(teacher, db, extra):
    body = {"title": "Zadanie", "deadline": future(), **extra}
    assert teacher.post("/api/v1/tasks", json=body).status_code == 422
    assert db.query(Task).count() == 0


@pytest.mark.parametrize("extra", [{"created_by": 2}, {"id": 77}, {"is_expired": True}])
def test_task_update_rejects_server_fields(teacher, task_id, db, extra):
    assert teacher.patch(f"/api/v1/tasks/{task_id}", json=extra).status_code == 422
    db.expire_all()
    assert db.get(Task, task_id).created_by == 1


def test_foreign_teacher_cannot_take_over_task(task_id, db):
    other = logged_in(OTHER_TEACHER)
    assert other.patch(f"/api/v1/tasks/{task_id}", json={"title": "Przejęte"}).status_code == 403
    db.expire_all()
    assert db.get(Task, task_id).title != "Przejęte"


# --- Rejestracja: eskalacja roli i nadpisanie pól ---------------------------------

@pytest.mark.parametrize("role", ["admin", "ADMIN", "Teacher", "superuser", "", None, 1, ["teacher"]])
def test_register_rejects_unknown_roles(db, role):
    res = anonymous().post("/api/v1/auth/register", json={**STUDENT, "role": role})
    assert res.status_code == 422
    assert db.query(User).count() == 0


def test_register_ignores_server_controlled_fields(db):
    payload = {
        **STUDENT,
        "id": 999,
        "hashed_password": "$2b$12$attackercontrolledhashxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        "created_at": "2000-01-01T00:00:00Z",
        "is_admin": True,
    }
    res = anonymous().post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    body = res.json()
    assert body["id"] == 1
    assert not body["created_at"].startswith("2000")
    assert "is_admin" not in body
    # Hasło jest hashowane przez serwer – logowanie podanym hasłem działa.
    login(STUDENT)
    user = db.get(User, 1)
    assert user.hashed_password != payload["hashed_password"]
    assert user.role == "student"


# --- Ekspozycja danych w odpowiedziach -------------------------------------------

def test_responses_never_contain_password_hash(teacher, student, task_id):
    bodies = [
        anonymous().post("/api/v1/auth/register", json={**OTHER_TEACHER}).text,
        student.get("/api/v1/auth/me").text,
        anonymous().post("/api/v1/auth/login", json={"email": STUDENT["email"],
                                                      "password": STUDENT["password"]}).text,
        teacher.get(f"/api/v1/tasks/{task_id}").text,
    ]
    for body in bodies:
        assert "hashed_password" not in body
        assert "$2b$" not in body
        assert STUDENT["password"] not in body
