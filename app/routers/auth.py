from fastapi import APIRouter, Depends, Response, status

from app.config import settings
from app.dependencies import get_current_user
from app.schemas.auth import LoginResponse, MessageResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from app.security import create_access_token
from app.services.auth_service import authenticate_user, register_user

router = APIRouter(prefix="/api/v1/auth", tags=["Uwierzytelnianie"])


def _set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def _clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


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
    summary="Logowanie użytkownika (ustawia ciasteczko HttpOnly z tokenem JWT)"
)
def login(data: UserLoginRequest, response: Response):
    user = authenticate_user(data)
    token = create_access_token(user_id=user.id, role=user.role)
    _set_auth_cookie(response, token)
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse(
        message="Logowanie zakończone sukcesem.",
        user=user
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Wylogowanie użytkownika (usuwa ciasteczko z tokenem)"
)
def logout(response: Response):
    _clear_auth_cookie(response)
    return MessageResponse(message="Wylogowano pomyślnie.")


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Dane aktualnie zalogowanego użytkownika"
)
def me(response: Response, current_user: UserResponse = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return current_user
