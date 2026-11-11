from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from app.config import settings
from app.schemas.auth import UserResponse
from app.security import decode_access_token
from app.services.auth_service import get_user_by_id, user_record_to_response


def get_current_user(request: Request) -> UserResponse:
    """Odczytuje JWT wyłącznie z ciasteczka HttpOnly i zwraca zalogowanego użytkownika."""
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak autoryzacji. Zaloguj się."
        )

    payload = decode_access_token(token)

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesja wygasła lub jest nieprawidłowa. Zaloguj się ponownie."
        )

    user_record = get_user_by_id(user_id)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesja wygasła lub jest nieprawidłowa. Zaloguj się ponownie."
        )

    # Rola zawsze pochodzi z bazy, a nie z tokenu – zmiana roli działa natychmiast.
    return user_record_to_response(user_record)


def require_role(*allowed_roles: str) -> Callable[..., UserResponse]:
    """Fabryka zależności RBAC, np. Depends(require_role("teacher"))."""

    def _checker(user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Brak uprawnień do wykonania tej operacji."
            )
        return user

    return _checker
