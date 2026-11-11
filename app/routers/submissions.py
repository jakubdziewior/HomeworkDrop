from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, Response, UploadFile, status
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.schemas.auth import UserResponse
from app.schemas.submission import GradeRequest, SubmissionResponse
from app.services import submission_service
from app.services.file_validation import allowed_extensions_label

router = APIRouter(prefix="/api/v1", tags=["Zgłoszenia (pliki)"])

TaskId = Path(..., ge=1, description="Identyfikator zadania")
SubmissionId = Path(..., ge=1, description="Identyfikator zgłoszenia")

_ALLOWED_UPLOAD_FIELDS = {"file"}


async def reject_extra_form_fields(request: Request) -> None:
    """
    Ochrona przed Mass Assignment w formularzu multipart: FastAPI domyślnie ignoruje
    nadmiarowe pola (np. grade=5.0), tu są jawnie odrzucane.
    """
    form = await request.form()  # formularz jest już sparsowany i zbuforowany
    extra = sorted(set(form.keys()) - _ALLOWED_UPLOAD_FIELDS)
    if extra:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Niedozwolone pola w żądaniu: {', '.join(extra)}."
        )


@router.post(
    "/tasks/{task_id}/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Wgranie rozwiązania (tylko student, przed terminem)",
    description=(
        f"Dozwolone rozszerzenia: {allowed_extensions_label()}. "
        f"Maksymalny rozmiar: {settings.MAX_UPLOAD_SIZE_MB} MB. "
        "Ponowne wgranie przed terminem zastępuje poprzedni plik (200), "
        "o ile zgłoszenie nie zostało jeszcze ocenione (409)."
    ),
    dependencies=[Depends(reject_extra_form_fields)],
)
def upload_submission(
    response: Response,
    task_id: int = TaskId,
    file: UploadFile = File(..., description="Plik z rozwiązaniem"),
    student: UserResponse = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    submission, created = submission_service.upload_submission(db, task_id, file, student)
    if not created:
        response.status_code = status.HTTP_200_OK
    return submission


@router.get(
    "/tasks/{task_id}/submissions",
    response_model=List[SubmissionResponse],
    summary="Lista zgłoszeń do zadania (tylko prowadzący – autor zadania)",
)
def list_submissions(
    task_id: int = TaskId,
    teacher: UserResponse = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    return submission_service.list_for_task(db, task_id, teacher)


@router.get(
    "/tasks/{task_id}/submissions/me",
    response_model=SubmissionResponse,
    summary="Własne zgłoszenie do zadania (tylko student)",
)
def get_my_submission(
    task_id: int = TaskId,
    student: UserResponse = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    return submission_service.get_own_submission(db, task_id, student)


@router.put(
    "/submissions/{submission_id}/grade",
    response_model=SubmissionResponse,
    summary="Wystawienie lub zmiana oceny (tylko prowadzący – autor zadania)",
    description="Przyjmowane są wyłącznie pola `grade` i `feedback`; każde inne pole skutkuje błędem 422.",
)
def grade_submission(
    data: GradeRequest,
    submission_id: int = SubmissionId,
    teacher: UserResponse = Depends(require_role("teacher")),
    db: Session = Depends(get_db),
):
    return submission_service.grade_submission(db, submission_id, data, teacher)


@router.get(
    "/submissions/{submission_id}/download",
    response_class=FileResponse,
    summary="Pobranie pliku zgłoszenia (autor zgłoszenia lub prowadzący zadania)",
)
def download_submission(
    submission_id: int = SubmissionId,
    user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    path, download_name = submission_service.get_download(db, submission_id, user)
    return FileResponse(
        path,
        # Zawsze jako załącznik i z ogólnym typem – przeglądarka nie wyrenderuje
        # pliku w kontekście aplikacji (ochrona przed stored XSS).
        media_type="application/octet-stream",
        filename=download_name,
        content_disposition_type="attachment",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "Cache-Control": "no-store",
        },
    )
