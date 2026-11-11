from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.dependencies import get_current_user, require_role
from app.main import app
from app.security import create_access_token, decode_access_token
from app.models import User

client = TestClient(app, base_url="https://testserver")

STUDENT = {
    "email": "p.zielinski@student.edu.pl",
    "password": "HasloStudenta123!",
    "full_name": "Piotr Zieliński",
    "role": "student",
}
TEACHER = {
    "email": "t.kaminski@uczelnia.edu.pl",
    "password": "HasloProwadzacego123!",
    "full_name": "dr Tomasz Kamiński",
    "role": "teacher",
}


@pytest.fixture(autouse=True)
def clean_state():
    client.cookies.clear()
    yield
    client.cookies.clear()


def _register_and_login(c: TestClient, user: dict):
    assert c.post("/api/v1/auth/register", json=user).status_code == 201
    return c.post("/api/v1/auth/login", json={"email": user["email"], "password": user["password"]})


def test_login_sets_secure_httponly_cookie():
    res = _register_and_login(client, STUDENT)
    assert res.status_code == 200

    set_cookie = res.headers["set-cookie"]
    assert set_cookie.startswith(f"{settings.AUTH_COOKIE_NAME}=")
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=strict" in set_cookie
    assert "Path=/" in set_cookie
    assert f"Max-Age={settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}" in set_cookie

    # Token nie może trafiać do treści odpowiedzi (dostępnej dla JS).
    assert "token" not in res.text.lower().replace("access_token", "")
    assert res.headers["cache-control"] == "no-store"


def test_token_claims():
    _register_and_login(client, TEACHER)
    token = client.cookies.get(settings.AUTH_COOKIE_NAME)
    payload = decode_access_token(token)
    assert payload["sub"] == "1"
    assert payload["role"] == "teacher"
    assert payload["iss"] == settings.JWT_ISSUER
    assert payload["aud"] == settings.JWT_AUDIENCE
    assert payload["exp"] > payload["iat"]
    assert "password" not in payload and "hashed_password" not in payload


def test_me_returns_current_user():
    _register_and_login(client, STUDENT)
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 200
    assert res.json()["email"] == STUDENT["email"]
    assert res.json()["role"] == "student"


def test_me_without_cookie_returns_401():
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_bearer_header_is_not_accepted():
    _register_and_login(client, STUDENT)
    token = client.cookies.get(settings.AUTH_COOKIE_NAME)
    client.cookies.clear()
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_logout_clears_cookie():
    _register_and_login(client, STUDENT)
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 200
    assert f'{settings.AUTH_COOKIE_NAME}=""' in res.headers["set-cookie"]
    assert "Max-Age=0" in res.headers["set-cookie"]
    assert client.get("/api/v1/auth/me").status_code == 401


def test_failed_login_does_not_set_cookie():
    client.post("/api/v1/auth/register", json=STUDENT)
    res = client.post("/api/v1/auth/login", json={"email": STUDENT["email"], "password": "ZleHaslo123!"})
    assert res.status_code == 401
    assert "set-cookie" not in res.headers


def test_expired_token_rejected():
    client.post("/api/v1/auth/register", json=STUDENT)
    expired = create_access_token(user_id=1, role="student", expires_minutes=-1)
    client.cookies.set(settings.AUTH_COOKIE_NAME, expired)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_token_signed_with_other_key_rejected():
    client.post("/api/v1/auth/register", json=STUDENT)
    now = datetime.now(timezone.utc)
    forged = jwt.encode(
        {
            "sub": "1", "role": "teacher", "iat": now, "exp": now + timedelta(minutes=5),
            "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
        },
        "atakujacy-zna-inny-klucz-" * 3,
        algorithm="HS256",
    )
    client.cookies.set(settings.AUTH_COOKIE_NAME, forged)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_alg_none_token_rejected():
    client.post("/api/v1/auth/register", json=STUDENT)
    now = datetime.now(timezone.utc)
    unsigned = jwt.encode(
        {
            "sub": "1", "role": "teacher", "iat": now, "exp": now + timedelta(minutes=5),
            "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE,
        },
        None,
        algorithm="none",
    )
    client.cookies.set(settings.AUTH_COOKIE_NAME, unsigned)
    assert client.get("/api/v1/auth/me").status_code == 401


def test_token_for_deleted_user_rejected(db):
    _register_and_login(client, STUDENT)
    db.delete(db.get(User, 1))
    db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_garbage_token_rejected():
    client.cookies.set(settings.AUTH_COOKIE_NAME, "to.nie.jest.jwt")
    assert client.get("/api/v1/auth/me").status_code == 401


# --- RBAC -----------------------------------------------------------------

rbac_app = FastAPI()


@rbac_app.post("/grades")
def create_grade(user=Depends(require_role("teacher"))):
    return {"ok": True, "by": user.email}


@rbac_app.get("/whoami")
def whoami(user=Depends(get_current_user)):
    return {"role": user.role}


def _rbac_client_for(user: dict) -> TestClient:
    _register_and_login(client, user)
    rbac_client = TestClient(rbac_app, base_url="https://testserver")
    rbac_client.cookies.set(settings.AUTH_COOKIE_NAME, client.cookies.get(settings.AUTH_COOKIE_NAME))
    return rbac_client


def test_require_role_allows_teacher():
    rbac_client = _rbac_client_for(TEACHER)
    res = rbac_client.post("/grades")
    assert res.status_code == 200
    assert res.json()["by"] == TEACHER["email"]


def test_require_role_blocks_student():
    rbac_client = _rbac_client_for(STUDENT)
    res = rbac_client.post("/grades")
    assert res.status_code == 403


def test_require_role_without_login_returns_401():
    rbac_client = TestClient(rbac_app, base_url="https://testserver")
    assert rbac_client.post("/grades").status_code == 401
