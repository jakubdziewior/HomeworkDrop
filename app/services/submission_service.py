from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Submission
from app.schemas.auth import UserResponse
from app.schemas.submission import GradeRequest, SubmissionResponse
from app.services import storage_service
from app.services.deadline_service import validate_submission_deadline
from app.services.file_validation import get_extension, sanitize_display_name, validate_file
from app.services.task_service import get_task_record


def _to_response(sub: Submission) -> SubmissionResponse:
    return SubmissionResponse(
        id=sub.id,
        task_id=sub.task_id,
        student_id=sub.student_id,
        original_filename=sub.original_filename,
        content_type=sub.content_type,
        size_bytes=sub.size_bytes,
        sha256=sub.sha256,
        submitted_at=sub.submitted_at,
        updated_at=sub.updated_at,
        status=sub.status,
        grade=sub.grade,
        feedback=sub.feedback,
        graded_by=sub.graded_by,
        graded_at=sub.graded_at,
    )


def _find_for_student(db: Session, task_id: int, student_id: int) -> Optional[Submission]:
    return db.scalar(
        select(Submission).where(Submission.task_id == task_id, Submission.student_id == student_id)
    )


def _get_or_404(db: Session, submission_id: int) -> Submission:
    sub = db.get(Submission, submission_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zgłoszenie nie istnieje.")
    return sub


def _uploaded_size(upload: UploadFile) -> int:
    upload.file.seek(0, 2)
    size = upload.file.tell()
    upload.file.seek(0)
    return size


def upload_submission(
    db: Session, task_id: int, upload: UploadFile, student: UserResponse
) -> Tuple[SubmissionResponse, bool]:
    """
    Zapisuje (lub podmienia) rozwiązanie studenta dla zadania.
    Zwraca (zgłoszenie, czy_utworzono_nowe).
    """
    task = get_task_record(db, task_id)
    validate_submission_deadline(task.deadline)

    existing = _find_for_student(db, task_id, student.id)
    if existing and existing.status == "graded":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zgłoszenie zostało już ocenione – nie można podmienić pliku."
        )

    size = _uploaded_size(upload)
    if size > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Przesyłany plik jest za duży. Maksymalny rozmiar to {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    filename = upload.filename or ""
    file_type = validate_file(filename, upload.content_type, upload.file, size)
    stored_name, sha256 = storage_service.save_file(upload.file, get_extension(filename))

    file_fields = {
        "original_filename": sanitize_display_name(filename),
        "stored_filename": stored_name,
        "content_type": file_type.mime,
        "size_bytes": size,
        "sha256": sha256,
        "updated_at": datetime.now(timezone.utc),
    }

    old_stored_name = existing.stored_filename if existing else None
    if existing:
        for field, value in file_fields.items():
            setattr(existing, field, value)
        sub = existing
    else:
        sub = Submission(task_id=task_id, student_id=student.id, status="submitted", **file_fields)
        db.add(sub)

    try:
        db.commit()
    except IntegrityError:
        # Np. równoległe pierwsze wgranie tego samego studenta (unikalne task_id + student_id).
        db.rollback()
        storage_service.delete_file(stored_name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zgłoszenie jest właśnie zapisywane. Spróbuj ponownie."
        )
    except Exception:
        db.rollback()
        storage_service.delete_file(stored_name)
        raise

    if old_stored_name:
        storage_service.delete_file(old_stored_name)
    return _to_response(sub), existing is None


def list_for_task(db: Session, task_id: int, teacher: UserResponse) -> List[SubmissionResponse]:
    task = get_task_record(db, task_id)
    if task.created_by != teacher.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Możesz przeglądać wyłącznie zgłoszenia do własnych zadań."
        )
    subs = db.scalars(
        select(Submission).where(Submission.task_id == task_id).order_by(Submission.submitted_at, Submission.id)
    ).all()
    return [_to_response(s) for s in subs]


def get_own_submission(db: Session, task_id: int, student: UserResponse) -> SubmissionResponse:
    get_task_record(db, task_id)
    sub = _find_for_student(db, task_id, student.id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nie przesłano jeszcze rozwiązania.")
    return _to_response(sub)


def _ensure_task_teacher(sub: Submission, user: UserResponse) -> None:
    if user.role != "teacher" or sub.task.created_by != user.id:
        # 404 zamiast 403 – nie ujawniamy istnienia zgłoszeń do cudzych zadań.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zgłoszenie nie istnieje.")


def get_download(db: Session, submission_id: int, user: UserResponse) -> Tuple[Path, str]:
    """
    Zwraca (ścieżka, nazwa_do_pobrania). Dostęp ma tylko autor zgłoszenia
    oraz prowadzący, który utworzył zadanie (ochrona przed IDOR).
    """
    sub = _get_or_404(db, submission_id)
    is_owner = user.role == "student" and sub.student_id == user.id
    if not is_owner:
        _ensure_task_teacher(sub, user)
    return storage_service.get_file_path(sub.stored_filename), sub.original_filename


def grade_submission(
    db: Session, submission_id: int, data: GradeRequest, teacher: UserResponse
) -> SubmissionResponse:
    """
    Wystawia lub zmienia ocenę. Ocenić może wyłącznie prowadzący, który utworzył zadanie.
    Pola graded_by / graded_at / status ustawia serwer – nigdy nie pochodzą od klienta.
    """
    sub = _get_or_404(db, submission_id)
    _ensure_task_teacher(sub, teacher)

    sub.grade = data.grade
    sub.feedback = data.feedback
    sub.status = "graded"
    sub.graded_by = teacher.id
    sub.graded_at = datetime.now(timezone.utc)
    db.commit()
    return _to_response(sub)
