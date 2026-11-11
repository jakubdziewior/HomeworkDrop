from typing import List

from fastapi import APIRouter, Depends, Path, Response, status

from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.schemas.auth import UserResponse
from app.schemas.task import TaskCreateRequest, TaskResponse, TaskUpdateRequest
from app.services import task_service

router = APIRouter(prefix="/api/v1/tasks", tags=["Zadania"])

TaskId = Path(..., ge=1, description="Identyfikator zadania")


@router.get(
    "",
    response_model=List[TaskResponse],
    summary="Lista zadań (każdy zalogowany użytkownik)"
)
def list_tasks(_: UserResponse = Depends(get_current_user), db: Session = Depends(get_db)):
    return task_service.list_tasks(db)


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Szczegóły zadania (każdy zalogowany użytkownik)"
)
def get_task(
    task_id: int = TaskId,
    _: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return task_service.get_task(db, task_id)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Utworzenie zadania (tylko prowadzący)"
)
def create_task(
    data: TaskCreateRequest,
    teacher: UserResponse = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    return task_service.create_task(db, data, teacher)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Edycja zadania (tylko prowadzący będący autorem)"
)
def update_task(
    data: TaskUpdateRequest,
    task_id: int = TaskId,
    teacher: UserResponse = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    return task_service.update_task(db, task_id, data, teacher)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Usunięcie zadania (tylko prowadzący będący autorem)"
)
def delete_task(
    task_id: int = TaskId,
    teacher: UserResponse = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    task_service.delete_task(db, task_id, teacher)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
