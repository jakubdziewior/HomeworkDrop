from datetime import datetime, timezone
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Task
from app.schemas.auth import UserResponse
from app.schemas.task import TaskCreateRequest, TaskResponse, TaskUpdateRequest
from app.services import storage_service
from app.services.deadline_service import is_deadline_passed


def _to_response(task: Task) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        deadline=task.deadline,
        created_by=task.created_by,
        created_at=task.created_at,
        updated_at=task.updated_at,
        is_expired=is_deadline_passed(task.deadline),
    )


def get_task_record(db: Session, task_id: int) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zadanie o podanym identyfikatorze nie istnieje."
        )
    return task


def _ensure_owner(task: Task, user: UserResponse) -> None:
    if task.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Możesz modyfikować wyłącznie zadania utworzone przez siebie."
        )


def list_tasks(db: Session) -> List[TaskResponse]:
    tasks = db.scalars(select(Task).order_by(Task.deadline, Task.id)).all()
    return [_to_response(t) for t in tasks]


def get_task(db: Session, task_id: int) -> TaskResponse:
    return _to_response(get_task_record(db, task_id))


def create_task(db: Session, data: TaskCreateRequest, author: UserResponse) -> TaskResponse:
    task = Task(
        title=data.title,
        description=data.description,
        deadline=data.deadline,
        created_by=author.id,
    )
    db.add(task)
    db.commit()
    return _to_response(task)


def update_task(db: Session, task_id: int, data: TaskUpdateRequest, user: UserResponse) -> TaskResponse:
    task = get_task_record(db, task_id)
    _ensure_owner(task, user)

    changes = data.model_dump(exclude_unset=True)
    if changes:
        for field, value in changes.items():
            setattr(task, field, value)
        task.updated_at = datetime.now(timezone.utc)
        db.commit()
    return _to_response(task)


def delete_task(db: Session, task_id: int, user: UserResponse) -> None:
    task = get_task_record(db, task_id)
    _ensure_owner(task, user)

    stored_files = [s.stored_filename for s in task.submissions]
    db.delete(task)  # zgłoszenia usuwane kaskadowo
    db.commit()

    # Pliki usuwane dopiero po udanym zatwierdzeniu transakcji.
    for stored_name in stored_files:
        storage_service.delete_file(stored_name)
