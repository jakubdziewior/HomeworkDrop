from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest, UserResponse
from app.security import hash_password, validate_password_strength, verify_password

# Hash używany, gdy użytkownik nie istnieje – logowanie trwa tyle samo,
# więc po czasie odpowiedzi nie da się sprawdzić, czy konto istnieje.
_DUMMY_HASH = hash_password("dummy-password-for-timing-1A!")


def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at,
    )


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.scalar(select(User).where(User.email == email.lower()))


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.get(User, user_id)


def register_user(db: Session, data: UserRegisterRequest) -> UserResponse:
    email_key = data.email.lower()
    duplicate = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Użytkownik o podanym adresie email już istnieje."
    )

    if get_user_by_email(db, email_key):
        raise duplicate

    validate_password_strength(data.password)

    user = User(
        email=email_key,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Równoległa rejestracja tego samego adresu – chroni unikalny indeks.
        db.rollback()
        raise duplicate
    return user_to_response(user)


def authenticate_user(db: Session, data: UserLoginRequest) -> UserResponse:
    user = get_user_by_email(db, data.email)
    password_ok = verify_password(data.password, user.hashed_password if user else _DUMMY_HASH)

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy adres email lub hasło."
        )
    return user_to_response(user)


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


def seed_demo_users(db: Session) -> None:
    """Tworzy konta testowe (tylko w środowisku deweloperskim)."""
    for demo in DEMO_USERS:
        if not get_user_by_email(db, demo["email"]):
            register_user(db, UserRegisterRequest(**demo))
