"""Testy schematu: ograniczenia muszą działać na poziomie bazy, niezależnie od API."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, StatementError

from app.database import engine, init_db
from app.models import Submission, Task, User


def _user(db, email="s@student.edu.pl", role="student") -> User:
    u = User(email=email, hashed_password="x", full_name="Jan Kowalski", role=role)
    db.add(u)
    db.commit()
    return u


def _task(db, author: User) -> Task:
    t = Task(title="Zadanie", description="", deadline=datetime.now(timezone.utc) + timedelta(days=1),
             created_by=author.id)
    db.add(t)
    db.commit()
    return t


def _submission(db, task: Task, student: User, **overrides) -> Submission:
    data = dict(task_id=task.id, student_id=student.id, original_filename="a.pdf",
                stored_filename=overrides.pop("stored_filename", "a" * 32 + ".pdf"),
                content_type="application/pdf", size_bytes=10, sha256="0" * 64, status="submitted")
    data.update(overrides)
    s = Submission(**data)
    db.add(s)
    db.commit()
    return s


@pytest.fixture
def teacher(db):
    return _user(db, "t@uczelnia.edu.pl", "teacher")


@pytest.fixture
def student(db):
    return _user(db)


def test_tables_created():
    assert {"users", "tasks", "submissions"} <= set(inspect(engine).get_table_names())


def test_init_db_is_idempotent(db, student):
    init_db()
    init_db()
    assert db.get(User, student.id) is not None


def test_user_email_unique(db, student):
    with pytest.raises(IntegrityError):
        _user(db, student.email)


def test_user_role_check(db):
    with pytest.raises(IntegrityError):
        _user(db, "admin@x.pl", "admin")


def test_task_requires_existing_author(db):
    db.add(Task(title="X", description="", deadline=datetime.now(timezone.utc), created_by=999))
    with pytest.raises(IntegrityError):
        db.commit()


def test_one_submission_per_student_and_task(db, teacher, student):
    task = _task(db, teacher)
    _submission(db, task, student)
    with pytest.raises(IntegrityError):
        _submission(db, task, student, stored_filename="b" * 32 + ".pdf")


def test_stored_filename_unique(db, teacher, student):
    other = _user(db, "inny@student.edu.pl")
    task = _task(db, teacher)
    _submission(db, task, student)
    with pytest.raises(IntegrityError):
        _submission(db, task, other)


@pytest.mark.parametrize("grade", [1.0, 5.5, 4.2])
def test_grade_scale_check(db, teacher, student, grade):
    task = _task(db, teacher)
    with pytest.raises(IntegrityError):
        _submission(db, task, student, status="graded", grade=grade, graded_at=datetime.now(timezone.utc))


def test_grade_requires_graded_status(db, teacher, student):
    task = _task(db, teacher)
    with pytest.raises(IntegrityError):
        _submission(db, task, student, status="submitted", grade=5.0)


def test_graded_status_requires_grade(db, teacher, student):
    task = _task(db, teacher)
    with pytest.raises(IntegrityError):
        _submission(db, task, student, status="graded")


def test_valid_graded_submission(db, teacher, student):
    task = _task(db, teacher)
    sub = _submission(db, task, student, status="graded", grade=4.5, feedback="OK",
                      graded_by=teacher.id, graded_at=datetime.now(timezone.utc))
    db.expire_all()
    assert db.get(Submission, sub.id).grade == 4.5


def test_deleting_task_cascades_to_submissions(db, teacher, student):
    task = _task(db, teacher)
    _submission(db, task, student)
    db.delete(task)
    db.commit()
    assert db.query(Submission).count() == 0


def test_cannot_delete_teacher_with_tasks(db, teacher):
    _task(db, teacher)
    db.delete(teacher)
    with pytest.raises(IntegrityError):
        db.commit()


def test_datetimes_stored_and_returned_in_utc(db, teacher):
    warsaw = timezone(timedelta(hours=2))
    deadline = datetime(2030, 6, 1, 12, 0, tzinfo=warsaw)
    task = Task(title="Strefa", description="", deadline=deadline, created_by=teacher.id)
    db.add(task)
    db.commit()
    db.expire_all()

    loaded = db.get(Task, task.id).deadline
    assert loaded.tzinfo is not None
    assert loaded == deadline
    assert loaded.utcoffset() == timedelta(0)


def test_naive_datetime_rejected(db, teacher):
    db.add(Task(title="X", description="", deadline=datetime(2030, 1, 1), created_by=teacher.id))
    with pytest.raises(StatementError):
        db.commit()
