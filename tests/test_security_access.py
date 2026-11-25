from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Task, User


def _future_iso(days: int = 3) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _register_and_login(email: str, password: str, full_name: str, role: str) -> TestClient:
    client = TestClient(app, base_url="https://testserver")
    assert client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role,
        },
    ).status_code == 201
    assert client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    ).status_code == 200
    return client


@pytest.mark.security
@pytest.mark.parametrize(
    "weak_password",
    [
        "Krot1!",
        "tylko_male_1!",
        "BEZ_CYFRY_ZNAK!",
        "BezZnakuSpecjalnego123",
    ],
)
def test_security_weak_passwords_rejected_on_registration(weak_password, db):
    client = TestClient(app, base_url="https://testserver")
    res = client.post(
        "/api/v1/auth/register",
        json={
            "email": "p.zielinski@student.edu.pl",
            "password": weak_password,
            "full_name": "Piotr Zieliński",
            "role": "student",
        },
    )
    assert res.status_code in (400, 422)
    assert db.query(User).count() == 0


@pytest.mark.security
def test_security_unauthenticated_requests_blocked():
    anon = TestClient(app, base_url="https://testserver")
    assert anon.get("/api/v1/auth/me").status_code == 401
    assert anon.get("/api/v1/tasks").status_code == 401
    assert (
        anon.post(
            "/api/v1/tasks",
            json={"title": "Nieautoryzowane", "description": "", "deadline": _future_iso()},
        ).status_code
        == 401
    )
    assert anon.patch("/api/v1/tasks/1", json={"title": "Zmiana"}).status_code == 401
    assert anon.delete("/api/v1/tasks/1").status_code == 401


@pytest.mark.security
def test_security_student_cannot_create_update_or_delete_tasks_rbac(db):
    teacher = _register_and_login(
        "t.kaminski@uczelnia.edu.pl",
        "HasloProwadzacego123!",
        "dr Tomasz Kamiński",
        "teacher",
    )
    task = teacher.post(
        "/api/v1/tasks",
        json={"title": "Zadanie chronione", "description": "Opis", "deadline": _future_iso()},
    ).json()

    student = _register_and_login(
        "p.zielinski@student.edu.pl",
        "HasloStudenta123!",
        "Piotr Zieliński",
        "student",
    )

    assert (
        student.post(
            "/api/v1/tasks",
            json={"title": "Próba studenta", "description": "", "deadline": _future_iso()},
        ).status_code
        == 403
    )
    assert student.patch(f"/api/v1/tasks/{task['id']}", json={"title": "Zmiana"}).status_code == 403
    assert student.delete(f"/api/v1/tasks/{task['id']}").status_code == 403

    stored = db.get(Task, task["id"])
    assert stored is not None
    assert stored.title == "Zadanie chronione"


@pytest.mark.security
def test_security_teacher_cannot_modify_or_delete_other_teachers_task(db):
    owner = _register_and_login(
        "t.kaminski@uczelnia.edu.pl",
        "HasloProwadzacego123!",
        "dr Tomasz Kamiński",
        "teacher",
    )
    task = owner.post(
        "/api/v1/tasks",
        json={"title": "Zadanie pierwszego prowadzącego", "description": "Oryginał", "deadline": _future_iso()},
    ).json()

    other_teacher = _register_and_login(
        "a.kowalczyk@uczelnia.edu.pl",
        "HasloInnego123!",
        "dr Anna Kowalczyk",
        "teacher",
    )

    assert (
        other_teacher.patch(
            f"/api/v1/tasks/{task['id']}",
            json={"title": "Podmiana cudzego zadania"},
        ).status_code
        == 403
    )
    assert other_teacher.delete(f"/api/v1/tasks/{task['id']}").status_code == 403

    stored = db.get(Task, task["id"])
    assert stored is not None
    assert stored.title == "Zadanie pierwszego prowadzącego"


@pytest.mark.security
def test_security_registration_cannot_escalate_privileges_or_leak_hash(db):
    client = TestClient(app, base_url="https://testserver")
    escalation = client.post(
        "/api/v1/auth/register",
        json={
            "email": "p.zielinski@student.edu.pl",
            "password": "HasloStudenta123!",
            "full_name": "Piotr Zieliński",
            "role": "superadmin",
        },
    )
    assert escalation.status_code == 422
    assert db.query(User).count() == 0

    valid = client.post(
        "/api/v1/auth/register",
        json={
            "email": "p.zielinski@student.edu.pl",
            "password": "HasloStudenta123!",
            "full_name": "Piotr Zieliński",
            "role": "student",
        },
    )
    assert valid.status_code == 201
    body = valid.json()
    assert "hashed_password" not in body
    assert "password" not in body
