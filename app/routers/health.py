from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_class=JSONResponse, status_code=200)
def health_check():
    return {"status": "ok"}
