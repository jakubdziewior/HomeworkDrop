from fastapi import APIRouter, status
from app.schemas.auth import LoginResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/api/v1/auth", tags=["Uwierzytelnianie"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rejestracja nowego użytkownika"
)
def register(data: UserRegisterRequest):
    return register_user(data)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Logowanie użytkownika"
)
def login(data: UserLoginRequest):
    user = authenticate_user(data)
    return LoginResponse(
        message="Logowanie zakończone sukcesem.",
        user=user
    )
