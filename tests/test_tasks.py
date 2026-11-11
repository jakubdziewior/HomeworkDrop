from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Task

URL = "/api/v1/tasks"

STUDENT = {
    "email": "p.zielinski@student.edu.pl",
    "password": "HasloStudenta123!",
    "full_name": "Piotr Zieliński",
    "role": "student",
}
TEACHER = {
    "email": "t.kaminski@uczelnia.edu.pl",
    "password": "HasloProwadzacego123!",
    "full_name": "dr Tomasz Kamiński",
    "role": "teacher",
}
OTHER_TEACHER = {
    "email": "a.nowak@uczelnia.edu.pl",
    "password": "InneHaslo123!",
    "full_name": "dr Anna Nowak",
    "role": "teacher",
}


def _future(hours: int = 48) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past(hours: int = 1) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def _logged_in(user: dict) -> TestClient:
    c = TestClient(app, base_url="https://testserver")
    assert c.post("/api/v1/auth/register", json=user).status_code == 201
    res = c.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})
    assert res.status_code == 200
    return c


@pytest.fixture(autouse=True)
def clean_state():
    yield


@pytest.fixture
def teacher():
    return _logged_in(TEACHER)


@pytest.fixture
def student():
    return _logged_in(STUDENT)


@pytest.fixture
def other_teacher():
    return _logged_in(OTHER_TEACHER)


def _payload(**overrides) -> dict:
    data = {
        "title": "Implementacja potoku CI/CD",
        "description": "Pipeline z testami i skanowaniem SAST.",
        "deadline": _future(),
    }
    data.update(overrides)
    return data


def _create(client: TestClient, **overrides) -> dict:
    res = client.post(URL, json=_payload(**overrides))
    assert res.status_code == 201, res.text
    return res.json()


# --- Tworzenie -------------------------------------------------------------

def test_teacher_can_create_task(teacher):
    task = _create(teacher, title="  Analiza podatności  ")
    assert task["id"] == 1
    assert task["title"] == "Analiza podatności"
    assert task["created_by"] == 1
    assert task["is_expired"] is False


def test_student_cannot_create_task(student, db):
    res = student.post(URL, json=_payload())
    assert res.status_code == 403
    assert db.query(Task).count() == 0


def test_anonymous_cannot_create_task():
    anon = TestClient(app, base_url="https://testserver")
    assert anon.post(URL, json=_payload()).status_code == 401


def test_create_rejects_past_deadline(teacher):
    res = teacher.post(URL, json=_payload(deadline=_past()))
    assert res.status_code == 422


def test_create_rejects_naive_deadline(teacher):
    naive = (datetime.now() + timedelta(days=1)).replace(microsecond=0).isoformat()
    assert teacher.post(URL, json=_payload(deadline=naive)).status_code == 422


@pytest.mark.parametrize("title", ["", "   ", "ab", "x" * 201])
def test_create_rejects_invalid_title(teacher, title):
    assert teacher.post(URL, json=_payload(title=title)).status_code == 422


def test_create_rejects_extra_fields_mass_assignment(teacher, db):
    res = teacher.post(URL, json=_payload(created_by=999, id=42, is_expired=True))
    assert res.status_code == 422
    assert db.query(Task).count() == 0


# --- Odczyt ----------------------------------------------------------------

def test_list_tasks_available_for_student_sorted_by_deadline(teacher, student):
    _create(teacher, title="Późniejsze zadanie", deadline=_future(72))
    _create(teacher, title="Wcześniejsze zadanie", deadline=_future(24))

    res = student.get(URL)
    assert res.status_code == 200
    titles = [t["title"] for t in res.json()]
    assert titles == ["Wcześniejsze zadanie", "Późniejsze zadanie"]


def test_get_task_by_id(teacher, student):
    task = _create(teacher)
    res = student.get(f"{URL}/{task['id']}")
    assert res.status_code == 200
    assert res.json()["title"] == task["title"]


def test_get_nonexistent_task_returns_404(student):
    assert student.get(f"{URL}/999").status_code == 404


def test_invalid_task_id_returns_422(student):
    assert student.get(f"{URL}/0").status_code == 422
    assert student.get(f"{URL}/abc").status_code == 422


def test_anonymous_cannot_list_tasks():
    anon = TestClient(app, base_url="https://testserver")
    assert anon.get(URL).status_code == 401


def test_is_expired_flag(teacher, db):
    task = _create(teacher)
    db.get(Task, task["id"]).deadline = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.commit()
    assert teacher.get(f"{URL}/{task['id']}").json()["is_expired"] is True


# --- Edycja ----------------------------------------------------------------

def test_teacher_can_partially_update_own_task(teacher):
    task = _create(teacher)
    new_deadline = _future(96)

    res = teacher.patch(f"{URL}/{task['id']}", json={"title": "Nowy tytuł", "deadline": new_deadline})
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "Nowy tytuł"
    assert body["description"] == task["description"]
    assert datetime.fromisoformat(body["deadline"]) == datetime.fromisoformat(new_deadline)
    assert body["updated_at"] >= task["updated_at"]


def test_student_cannot_update_task(teacher, student, db):
    task = _create(teacher)
    res = student.patch(f"{URL}/{task['id']}", json={"title": "Przejęte zadanie"})
    assert res.status_code == 403
    assert db.get(Task, task["id"]).title == task["title"]


def test_teacher_cannot_update_foreign_task(teacher, other_teacher):
    task = _create(teacher)
    res = other_teacher.patch(f"{URL}/{task['id']}", json={"title": "Cudze zadanie"})
    assert res.status_code == 403


def test_update_rejects_mass_assignment(teacher, db):
    task = _create(teacher)
    res = teacher.patch(f"{URL}/{task['id']}", json={"created_by": 2})
    assert res.status_code == 422
    assert db.get(Task, task["id"]).created_by == 1


def test_update_rejects_null_title(teacher):
    task = _create(teacher)
    assert teacher.patch(f"{URL}/{task['id']}", json={"title": None}).status_code == 422


def test_update_rejects_past_deadline(teacher):
    task = _create(teacher)
    assert teacher.patch(f"{URL}/{task['id']}", json={"deadline": _past()}).status_code == 422


def test_update_nonexistent_task_returns_404(teacher):
    assert teacher.patch(f"{URL}/999", json={"title": "Cokolwiek"}).status_code == 404


# --- Usuwanie --------------------------------------------------------------

def test_teacher_can_delete_own_task(teacher):
    task = _create(teacher)
    res = teacher.delete(f"{URL}/{task['id']}")
    assert res.status_code == 204
    assert res.content == b""
    assert teacher.get(f"{URL}/{task['id']}").status_code == 404


def test_student_cannot_delete_task(teacher, student, db):
    task = _create(teacher)
    assert student.delete(f"{URL}/{task['id']}").status_code == 403
    assert db.get(Task, task["id"]) is not None


def test_teacher_cannot_delete_foreign_task(teacher, other_teacher, db):
    task = _create(teacher)
    assert other_teacher.delete(f"{URL}/{task['id']}").status_code == 403
    assert db.get(Task, task["id"]) is not None


def test_delete_nonexistent_task_returns_404(teacher):
    assert teacher.delete(f"{URL}/999").status_code == 404
