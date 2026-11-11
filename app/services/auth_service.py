from datetime import datetime, timezone
from typing import Dict, Optional
from fastapi import HTTPException, status
from app.schemas.auth import UserLoginRequest, UserRegisterRequest, UserResponse
from app.security import hash_password, validate_password_strength, verify_password

_users_db: Dict[str, dict] = {}
_next_id: int = 1


def user_record_to_response(user_record: dict) -> UserResponse:
    return UserResponse(
        id=user_record["id"],
        email=user_record["email"],
        full_name=user_record["full_name"],
        role=user_record["role"],
        created_at=user_record["created_at"]
    )


def register_user(data: UserRegisterRequest) -> UserResponse:
    global _next_id
    email_key = data.email.lower()

    if email_key in _users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Użytkownik o podanym adresie email już istnieje."
        )

    validate_password_strength(data.password)
    hashed_pwd = hash_password(data.password)

    user_id = _next_id
    _next_id += 1

    user_record = {
        "id": user_id,
        "email": email_key,
        "hashed_password": hashed_pwd,
        "full_name": data.full_name,
        "role": data.role,
        "created_at": datetime.now(timezone.utc)
    }
    _users_db[email_key] = user_record

    return user_record_to_response(user_record)


def authenticate_user(data: UserLoginRequest) -> UserResponse:
    email_key = data.email.lower()
    user_record = _users_db.get(email_key)

    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy adres email lub hasło."
        )

    if not verify_password(data.password, user_record["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy adres email lub hasło."
        )

    return user_record_to_response(user_record)


def get_user_by_email(email: str) -> Optional[dict]:
    return _users_db.get(email.lower())


def get_user_by_id(user_id: int) -> Optional[dict]:
    for user in _users_db.values():
        if user["id"] == user_id:
            return user
    return None


def reset_users_db() -> None:
    global _next_id
    _users_db.clear()
    _next_id = 1


DEMO_USERS = [
    {
        "email": "p.zielinski@student.edu.pl",
        "password": "HasloStudenta123!",
        "full_name": "Piotr Zieliński",
        "role": "student",
    },
    {
        "email": "t.kaminski@uczelnia.edu.pl",
        "password": "HasloProwadzacego123!",
        "full_name": "dr Tomasz Kamiński",
        "role": "teacher",
    },
]


def seed_demo_users() -> None:
    """Tworzy konta testowe (tylko w środowisku deweloperskim)."""
    for demo in DEMO_USERS:
        if demo["email"] not in _users_db:
            register_user(UserRegisterRequest(**demo))
