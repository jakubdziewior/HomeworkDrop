from datetime import datetime, timedelta, timezone
import io
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models import Task


def _future_iso(days: int = 3) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _register_and_login(email: str, password: str, full_name: str, role: str) -> TestClient:
    client = TestClient(app, base_url="https://testserver")
    reg_res = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role,
        },
    )
    assert reg_res.status_code == 201
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    return client


@pytest.mark.integration
def test_integration_teacher_register_login_create_and_list_task():
    teacher = _register_and_login(
        "t.kaminski@uczelnia.edu.pl",
        "HasloProwadzacego123!",
        "dr Tomasz Kamiński",
        "teacher",
    )

    me_res = teacher.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["role"] == "teacher"

    create_res = teacher.post(
        "/api/v1/tasks",
        json={
            "title": "Projekt DevSecOps Etap 3",
            "description": "Zestaw testów automatycznych aplikacji.",
            "deadline": _future_iso(5),
        },
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["is_expired"] is False

    list_res = teacher.get("/api/v1/tasks")
    assert list_res.status_code == 200
    tasks = list_res.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == created["id"]
    assert tasks[0]["title"] == "Projekt DevSecOps Etap 3"


@pytest.mark.integration
def test_integration_teacher_creates_updates_and_deletes_task():
    teacher = _register_and_login(
        "t.kaminski@uczelnia.edu.pl",
        "HasloProwadzacego123!",
        "dr Tomasz Kamiński",
        "teacher",
    )

    created = teacher.post(
        "/api/v1/tasks",
        json={
            "title": "Zadanie wstępne",
            "description": "Pierwsza wersja opisu.",
            "deadline": _future_iso(4),
        },
    ).json()
    task_id = created["id"]

    patch_res = teacher.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "title": "Zadanie zaktualizowane",
            "description": "Nowe wymagania projektowe.",
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Zadanie zaktualizowane"

    get_res = teacher.get(f"/api/v1/tasks/{task_id}")
    assert get_res.status_code == 200
    assert get_res.json()["description"] == "Nowe wymagania projektowe."

    del_res = teacher.delete(f"/api/v1/tasks/{task_id}")
    assert del_res.status_code == 204
    assert teacher.get(f"/api/v1/tasks/{task_id}").status_code == 404


@pytest.mark.integration
def test_integration_student_registers_logs_in_and_views_teacher_tasks():
    teacher = _register_and_login(
        "t.kaminski@uczelnia.edu.pl",
        "HasloProwadzacego123!",
        "dr Tomasz Kamiński",
        "teacher",
    )
    created = teacher.post(
        "/api/v1/tasks",
        json={
            "title": "Analiza zagrożeń",
            "description": "Model STRIDE",
            "deadline": _future_iso(7),
        },
    ).json()

    student = _register_and_login(
        "p.zielinski@student.edu.pl",
        "HasloStudenta123!",
        "Piotr Zieliński",
        "student",
    )

    list_res = student.get("/api/v1/tasks")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["id"] == created["id"]
    assert items[0]["created_by"] == created["created_by"]

    detail_res = student.get(f"/api/v1/tasks/{created['id']}")
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "Analiza zagrożeń"


@pytest.mark.integration
def test_integration_logout_invalidates_session_for_protected_endpoints():
    student = _register_and_login(
        "p.zielinski@student.edu.pl",
        "HasloStudenta123!",
        "Piotr Zieliński",
        "student",
    )

    assert student.get("/api/v1/auth/me").status_code == 200
    assert student.get("/api/v1/tasks").status_code == 200

    logout_res = student.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200
    assert student.get("/api/v1/auth/me").status_code == 401
    assert student.get("/api/v1/tasks").status_code == 401


@pytest.mark.integration
def test_integration_deadline_blocks_late_submission_after_task_creation(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))

    teacher = _register_and_login(
        "t.kaminski@uczelnia.edu.pl",
        "HasloProwadzacego123!",
        "dr Tomasz Kamiński",
        "teacher",
    )
    task = teacher.post(
        "/api/v1/tasks",
        json={
            "title": "Laboratorium z terminem",
            "description": "Oddanie przed deadline.",
            "deadline": _future_iso(1),
        },
    ).json()

    student = _register_and_login(
        "p.zielinski@student.edu.pl",
        "HasloStudenta123!",
        "Piotr Zieliński",
        "student",
    )

    on_time = student.post(
        f"/api/v1/tasks/{task['id']}/submissions",
        files={"file": ("rozwiazanie.txt", io.BytesIO(b"wersja pierwsza"), "text/plain")},
    )
    assert on_time.status_code == 201

    db_task = db.get(Task, task["id"])
    db_task.deadline = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.commit()

    late_attempt = student.post(
        f"/api/v1/tasks/{task['id']}/submissions",
        files={"file": ("rozwiazanie_v2.txt", io.BytesIO(b"spozniona wersja"), "text/plain")},
    )
    assert late_attempt.status_code == 400
    assert "blokada deadline" in late_attempt.json()["detail"]

    own = student.get(f"/api/v1/tasks/{task['id']}/submissions/me")
    assert own.status_code == 200
    assert own.json()["original_filename"] == "rozwiazanie.txt"
