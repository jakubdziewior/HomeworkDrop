"""
Testy integracyjne pełnego obiegu: rejestracja → zadanie → wgranie pracy → podgląd
i pobranie przez prowadzącego → ocena → wynik u studenta → termin → usunięcie zadania.
Każdy krok przechodzi przez prawdziwe API (HTTP + JWT w ciasteczku + baza + dysk).
"""

import hashlib
from datetime import datetime, timedelta, timezone

from app.models import Submission, Task
from tests.helpers import (
    OTHER_STUDENT, OTHER_TEACHER, PDF, STUDENT, TEACHER, THIRD_STUDENT,
    create_task, docx_bytes, grade, logged_in, login, register, stored_files, upload, zip_bytes,
)


def _expire_task(db, task_id: int) -> None:
    db.get(Task, task_id).deadline = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()


def test_full_submission_and_grading_lifecycle(upload_dir, db):
    # 1. Rejestracja i logowanie wszystkich uczestników.
    teacher = logged_in(TEACHER)
    alice = logged_in(STUDENT)
    bob = logged_in(OTHER_STUDENT)
    carol = logged_in(THIRD_STUDENT)

    # 2. Prowadzący tworzy zadanie, studenci je widzą.
    task_id = create_task(teacher, "Projekt zaliczeniowy DevSecOps")
    tasks = alice.get("/api/v1/tasks").json()
    assert [t["id"] for t in tasks] == [task_id]
    assert tasks[0]["is_expired"] is False

    # 3. Studenci wgrywają prace (różne formaty).
    zip_content = zip_bytes({"src/main.py": "print('hello')", "README.md": "# Projekt"})
    res_a = upload(alice, task_id, "raport_koncowy.pdf", PDF, "application/pdf")
    res_b = upload(bob, task_id, "projekt.zip", zip_content, "application/x-zip-compressed")
    assert res_a.status_code == 201 and res_b.status_code == 201
    sub_a, sub_b = res_a.json(), res_b.json()
    assert sub_a["status"] == sub_b["status"] == "submitted"
    assert len(stored_files(upload_dir)) == 2

    # 4. Bob poprawia pracę przed terminem – to samo zgłoszenie, nowy plik, stary usunięty.
    docx = docx_bytes()
    res_b2 = upload(bob, task_id, "projekt_v2.docx", docx,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert res_b2.status_code == 200
    assert res_b2.json()["id"] == sub_b["id"]
    assert res_b2.json()["original_filename"] == "projekt_v2.docx"
    assert len(stored_files(upload_dir)) == 2

    # 5. Prowadzący widzi oba zgłoszenia i pobiera pliki – zawartość i SHA-256 się zgadzają.
    listing = teacher.get(f"/api/v1/tasks/{task_id}/submissions").json()
    assert {s["student_id"] for s in listing} == {sub_a["student_id"], sub_b["student_id"]}
    for sub_id, expected in ((sub_a["id"], PDF), (sub_b["id"], docx)):
        dl = teacher.get(f"/api/v1/submissions/{sub_id}/download")
        assert dl.status_code == 200
        assert dl.content == expected
        listed = next(s for s in listing if s["id"] == sub_id)
        assert listed["sha256"] == hashlib.sha256(expected).hexdigest()
        assert listed["size_bytes"] == len(expected)

    # 6. Ocenianie.
    assert grade(teacher, sub_a["id"], {"grade": 5.0, "feedback": "Bardzo dobra praca."}).status_code == 200
    assert grade(teacher, sub_b["id"], {"grade": 3.5, "feedback": "Brakuje testów."}).status_code == 200

    # 7. Każdy student widzi wyłącznie swoją ocenę.
    mine_a = alice.get(f"/api/v1/tasks/{task_id}/submissions/me").json()
    mine_b = bob.get(f"/api/v1/tasks/{task_id}/submissions/me").json()
    assert (mine_a["grade"], mine_a["feedback"], mine_a["status"]) == (5.0, "Bardzo dobra praca.", "graded")
    assert (mine_b["grade"], mine_b["feedback"]) == (3.5, "Brakuje testów.")
    assert mine_a["graded_by"] == mine_b["graded_by"] == teacher.get("/api/v1/auth/me").json()["id"]
    assert carol.get(f"/api/v1/tasks/{task_id}/submissions/me").status_code == 404
    assert alice.get(f"/api/v1/submissions/{sub_b['id']}/download").status_code == 404

    # 8. Po ocenie plik jest zablokowany.
    assert upload(alice, task_id, "poprawka.pdf").status_code == 409

    # 9. Termin mija – spóźniony student nie może wgrać pracy, prowadzący nadal może zmienić ocenę.
    _expire_task(db, task_id)
    assert teacher.get(f"/api/v1/tasks/{task_id}").json()["is_expired"] is True
    late = upload(carol, task_id, "spozniony.pdf")
    assert late.status_code == 400
    assert grade(teacher, sub_b["id"], {"grade": 4.0, "feedback": "Po odwołaniu."}).status_code == 200
    assert bob.get(f"/api/v1/tasks/{task_id}/submissions/me").json()["grade"] == 4.0

    # 10. Usunięcie zadania usuwa zgłoszenia i pliki z dysku.
    assert teacher.delete(f"/api/v1/tasks/{task_id}").status_code == 204
    db.expire_all()
    assert db.query(Submission).count() == 0
    assert stored_files(upload_dir) == []
    assert alice.get(f"/api/v1/submissions/{sub_a['id']}/download").status_code == 404


def test_graded_by_points_to_grading_teacher(db):
    teacher_id = register(TEACHER)
    teacher = login(TEACHER)
    student = logged_in(STUDENT)
    task_id = create_task(teacher)
    sub_id = upload(student, task_id).json()["id"]

    body = grade(teacher, sub_id, {"grade": 4.5}).json()
    assert body["graded_by"] == teacher_id
    graded_at = datetime.fromisoformat(body["graded_at"])
    assert abs(datetime.now(timezone.utc) - graded_at) < timedelta(minutes=1)

    row = db.get(Submission, sub_id)
    assert (row.status, row.grade, row.graded_by) == ("graded", 4.5, teacher_id)


def test_grade_survives_new_login_session():
    teacher = logged_in(TEACHER)
    student = logged_in(STUDENT)
    task_id = create_task(teacher)
    sub_id = upload(student, task_id).json()["id"]
    grade(teacher, sub_id, {"grade": 4.0, "feedback": "OK"})

    assert student.post("/api/v1/auth/logout").status_code == 200
    fresh = login(STUDENT)
    body = fresh.get(f"/api/v1/tasks/{task_id}/submissions/me").json()
    assert (body["grade"], body["feedback"]) == (4.0, "OK")


def test_submissions_are_isolated_between_tasks_and_teachers():
    teacher = logged_in(TEACHER)
    other_teacher = logged_in(OTHER_TEACHER)
    student = logged_in(STUDENT)
    task_1 = create_task(teacher, "Zadanie prowadzącego A")
    task_2 = create_task(other_teacher, "Zadanie prowadzącego B")

    sub_1 = upload(student, task_1, "a.pdf").json()["id"]
    sub_2 = upload(student, task_2, "b.pdf").json()["id"]
    assert sub_1 != sub_2

    assert [s["id"] for s in teacher.get(f"/api/v1/tasks/{task_1}/submissions").json()] == [sub_1]
    assert [s["id"] for s in other_teacher.get(f"/api/v1/tasks/{task_2}/submissions").json()] == [sub_2]
    assert teacher.get(f"/api/v1/tasks/{task_2}/submissions").status_code == 403

    # Prowadzący nie może ocenić ani pobrać pracy z cudzego zadania.
    assert grade(teacher, sub_2, {"grade": 2.0}).status_code == 404
    assert teacher.get(f"/api/v1/submissions/{sub_2}/download").status_code == 404
    assert grade(other_teacher, sub_2, {"grade": 5.0}).status_code == 200

    # Ocena w jednym zadaniu nie blokuje wgrywania w drugim.
    assert upload(student, task_2, "c.pdf").status_code == 409
    assert upload(student, task_1, "d.pdf").status_code == 200


def test_reupload_before_grading_is_what_teacher_downloads(upload_dir):
    teacher = logged_in(TEACHER)
    student = logged_in(STUDENT)
    task_id = create_task(teacher)
    first = PDF + b"% wersja 1\n"
    second = PDF + b"% wersja 2\n"

    sub_id = upload(student, task_id, "v1.pdf", first).json()["id"]
    upload(student, task_id, "v2.pdf", second)
    dl = teacher.get(f"/api/v1/submissions/{sub_id}/download")
    assert dl.content == second
    assert "v2.pdf" in dl.headers["content-disposition"]
    assert len(stored_files(upload_dir)) == 1

    graded = grade(teacher, sub_id, {"grade": 3.0}).json()
    assert graded["sha256"] == hashlib.sha256(second).hexdigest()


def test_deadline_change_by_teacher_reopens_submissions(db):
    teacher = logged_in(TEACHER)
    student = logged_in(STUDENT)
    task_id = create_task(teacher)
    _expire_task(db, task_id)
    assert upload(student, task_id).status_code == 400

    new_deadline = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    assert teacher.patch(f"/api/v1/tasks/{task_id}", json={"deadline": new_deadline}).status_code == 200
    assert upload(student, task_id).status_code == 201


def test_teacher_listing_is_empty_before_any_upload():
    teacher = logged_in(TEACHER)
    task_id = create_task(teacher)
    res = teacher.get(f"/api/v1/tasks/{task_id}/submissions")
    assert res.status_code == 200
    assert res.json() == []
