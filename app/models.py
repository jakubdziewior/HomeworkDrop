"""
Schemat bazy danych HomeworkDrop.

    users 1 ──< tasks          (prowadzący tworzy zadania)
    users 1 ──< submissions    (student przesyła rozwiązania)
    tasks 1 ──< submissions    (max. jedno zgłoszenie studenta na zadanie)
    users 1 ──< submissions.graded_by (prowadzący wystawia ocenę)
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base
from app.schemas.submission import ALLOWED_GRADES

USER_ROLES = ("student", "teacher")
SUBMISSION_STATUSES = ("submitted", "graded")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sql_in(values) -> str:
    return ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in values)


class UTCDateTime(TypeDecorator):
    """
    Daty zawsze zapisywane w UTC i zwracane jako datetime ze strefą czasową.
    (SQLite nie przechowuje strefy – bez tego porównania z terminem byłyby błędne.)
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: Optional[datetime], dialect: Dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Daty zapisywane w bazie muszą zawierać strefę czasową.")
        value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value: Optional[datetime], dialect: Dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(f"role IN ({_sql_in(USER_ROLES)})", name="role_valid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)

    tasks: Mapped[List["Task"]] = relationship(back_populates="author")
    submissions: Mapped[List["Submission"]] = relationship(
        back_populates="student", foreign_keys="Submission.student_id"
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_deadline", "deadline"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    deadline: Mapped[datetime] = mapped_column(UTCDateTime)
    # RESTRICT – nie da się usunąć prowadzącego, który ma zadania.
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)

    author: Mapped[User] = relationship(back_populates="tasks")
    submissions: Mapped[List["Submission"]] = relationship(
        back_populates="task", cascade="all, delete-orphan", passive_deletes=True
    )


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (
        UniqueConstraint("task_id", "student_id", name="uq_submissions_task_student"),
        CheckConstraint(f"status IN ({_sql_in(SUBMISSION_STATUSES)})", name="status_valid"),
        CheckConstraint(f"grade IS NULL OR grade IN ({_sql_in(ALLOWED_GRADES)})", name="grade_scale"),
        CheckConstraint(
            "(status = 'graded' AND grade IS NOT NULL AND graded_at IS NOT NULL) "
            "OR (status = 'submitted' AND grade IS NULL)",
            name="grade_matches_status",
        ),
        CheckConstraint("size_bytes > 0", name="size_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Indeks na task_id zapewnia już unikalny klucz (task_id, student_id).
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Plik: nazwa na dysku to UUID; oryginalna nazwa służy tylko do wyświetlania.
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(64), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)

    # Ocena – ustawiana wyłącznie przez prowadzącego.
    status: Mapped[str] = mapped_column(String(16), default="submitted")
    grade: Mapped[Optional[float]] = mapped_column(Numeric(2, 1, asdecimal=False), nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    graded_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    graded_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, nullable=True)

    task: Mapped[Task] = relationship(back_populates="submissions")
    student: Mapped[User] = relationship(back_populates="submissions", foreign_keys=[student_id])
    grader: Mapped[Optional[User]] = relationship(foreign_keys=[graded_by])
