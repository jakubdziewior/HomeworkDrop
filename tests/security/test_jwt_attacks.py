"""
Scenariusze ataków na JWT: fałszowanie roli, podmiana algorytmu, manipulacja treścią,
brakujące / błędne claimy, przemycanie tokenu innymi kanałami oraz bezpieczna konfiguracja.
"""

import base64
import json
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError

from app.config import DEFAULT_SECRET_KEY, Settings, settings
from app.models import User
from app.security import create_access_token
from tests.helpers import STUDENT, TEACHER, anonymous, create_task, future, logged_in, register, upload

ME = "/api/v1/auth/me"


def _claims(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": "1", "role": "student", "iat": now, "nbf": now, "exp": now + timedelta(minutes=5),
        "iss": settings.JWT_ISSUER, "aud": settings.JWT_AUDIENCE, "jti": "test",
    }
    claims.update(overrides)
    return {k: v for k, v in claims.items() if v is not None}


def _token(key: str | None = None, algorithm: str | None = None, **overrides) -> str:
    return jwt.encode(_claims(**overrides), key if key is not None else settings.SECRET_KEY,
                      algorithm=algorithm or settings.ALGORITHM)


def _client_with(token: str):
    c = anonymous()
    c.cookies.set(settings.AUTH_COOKIE_NAME, token)
    return c


def _b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


@pytest.fixture
def student_id():
    return register(STUDENT)


# --- Sanity check: poprawnie podpisany token działa ----------------------------

def test_valid_handcrafted_token_accepted(student_id):
    assert _client_with(_token(sub=str(student_id))).get(ME).status_code == 200


# --- Eskalacja uprawnień przez claim "role" --------------------------------------

def test_role_claim_in_token_is_not_trusted(student_id):
    # Nawet poprawnie podpisany token z role=teacher nie daje uprawnień prowadzącego,
    # bo rola jest zawsze odczytywana z bazy.
    forged = _client_with(_token(sub=str(student_id), role="teacher"))
    assert forged.get(ME).json()["role"] == "student"
    res = forged.post("/api/v1/tasks", json={"title": "Atak", "deadline": future()})
    assert res.status_code == 403


def test_role_change_in_db_takes_effect_immediately(db):
    teacher = logged_in(TEACHER)
    db.get(User, 1).role = "student"
    db.commit()
    res = teacher.post("/api/v1/tasks", json={"title": "Zadanie", "deadline": future()})
    assert res.status_code == 403


def test_payload_tampering_invalidates_signature(student_id):
    teacher_id = register(TEACHER)
    header, payload, signature = _token(sub=str(student_id)).split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["sub"] = str(teacher_id)   # podmiana tożsamości bez zmiany podpisu
    tampered = f"{header}.{_b64(claims)}.{signature}"
    assert _client_with(tampered).get(ME).status_code == 401


def test_stripped_signature_rejected(student_id):
    header, payload, _ = _token(sub=str(student_id)).split(".")
    assert _client_with(f"{header}.{payload}.").get(ME).status_code == 401


# --- Algorytm --------------------------------------------------------------------

@pytest.mark.parametrize("alg", ["none", "None", "NONE", "nOnE"])
def test_none_algorithm_variants_rejected(student_id, alg):
    header = _b64({"alg": alg, "typ": "JWT"})
    payload = _b64({**_claims(sub=str(student_id)), "iat": 0, "nbf": 0,
                    "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())})
    assert _client_with(f"{header}.{payload}.").get(ME).status_code == 401


@pytest.mark.parametrize("alg", ["HS384", "HS512"])
def test_other_hmac_algorithm_with_valid_key_rejected(student_id, alg):
    # Serwer akceptuje wyłącznie skonfigurowany algorytm (algorithm pinning).
    assert _client_with(_token(algorithm=alg, sub=str(student_id))).get(ME).status_code == 401


@pytest.mark.parametrize("key", ["x", "secret", "changeme", DEFAULT_SECRET_KEY + "x", DEFAULT_SECRET_KEY[:-1]])
def test_weak_or_wrong_keys_rejected(student_id, key):
    assert _client_with(_token(key=key, sub=str(student_id))).get(ME).status_code == 401


def test_jwk_header_injection_rejected(student_id):
    attacker_key = "klucz-atakujacego-" * 4
    token = jwt.encode(_claims(sub=str(student_id)), attacker_key, algorithm="HS256",
                       headers={"jku": "https://evil.example/jwks.json", "kid": "../../dev/null"})
    assert _client_with(token).get(ME).status_code == 401


# --- Claimy ------------------------------------------------------------------------

@pytest.mark.parametrize("overrides", [
    {"iss": "evil-issuer"},
    {"aud": "inna-aplikacja"},
    {"aud": ["inna-aplikacja"]},
    {"exp": datetime.now(timezone.utc) - timedelta(seconds=5)},
    {"nbf": datetime.now(timezone.utc) + timedelta(hours=1)},
    {"sub": "abc"},
    {"sub": "999"},
    {"sub": "-1"},
    {"sub": "1 OR 1=1"},
], ids=["wrong-iss", "wrong-aud", "wrong-aud-list", "expired", "not-yet-valid",
        "sub-not-int", "sub-unknown-user", "sub-negative", "sub-sqli"])
def test_invalid_claims_rejected(student_id, overrides):
    assert _client_with(_token(**overrides)).get(ME).status_code == 401


@pytest.mark.parametrize("missing", ["exp", "iat", "sub", "iss", "aud"])
def test_required_claims_enforced(student_id, missing):
    claims = _claims(sub=str(student_id))
    claims.pop(missing)
    token = jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert _client_with(token).get(ME).status_code == 401


def test_token_lifetime_matches_configuration(student_id):
    token = create_access_token(student_id, "student")
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["exp"] - payload["iat"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert len(payload["jti"]) == 32


def test_each_login_issues_unique_jti():
    logged_in(STUDENT)
    c1, c2 = anonymous(), anonymous()
    creds = {"email": STUDENT["email"], "password": STUDENT["password"]}
    c1.post("/api/v1/auth/login", json=creds)
    c2.post("/api/v1/auth/login", json=creds)
    t1 = jwt.decode(c1.cookies.get(settings.AUTH_COOKIE_NAME), options={"verify_signature": False})
    t2 = jwt.decode(c2.cookies.get(settings.AUTH_COOKIE_NAME), options={"verify_signature": False})
    assert t1["jti"] != t2["jti"]


# --- Kanały przekazania tokenu ----------------------------------------------------

def test_token_only_accepted_from_cookie(student_id):
    token = _token(sub=str(student_id))
    c = anonymous()
    assert c.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert c.get(ME, params={"access_token": token}).status_code == 401
    assert c.get(ME, params={"token": token}).status_code == 401
    assert c.get(ME, headers={"X-Access-Token": token}).status_code == 401


def test_cookie_with_wrong_name_ignored(student_id):
    c = anonymous()
    c.cookies.set("token", _token(sub=str(student_id)))
    assert c.get(ME).status_code == 401


@pytest.mark.parametrize("value", ["", " ", "null", "undefined", "a.b", "a.b.c.d", "x" * 10000])
def test_malformed_cookie_values_rejected(value):
    assert _client_with(value).get(ME).status_code == 401


def test_protected_endpoints_require_token():
    teacher = logged_in(TEACHER)
    task_id = create_task(teacher)
    student = logged_in(STUDENT)
    sub_id = upload(student, task_id).json()["id"]
    anon = anonymous()
    for method, path in [
        ("GET", "/api/v1/tasks"),
        ("GET", f"/api/v1/tasks/{task_id}"),
        ("POST", "/api/v1/tasks"),
        ("PATCH", f"/api/v1/tasks/{task_id}"),
        ("DELETE", f"/api/v1/tasks/{task_id}"),
        ("GET", f"/api/v1/tasks/{task_id}/submissions"),
        ("GET", f"/api/v1/tasks/{task_id}/submissions/me"),
        ("POST", f"/api/v1/tasks/{task_id}/submissions"),
        ("PUT", f"/api/v1/submissions/{sub_id}/grade"),
        ("GET", f"/api/v1/submissions/{sub_id}/download"),
        ("GET", ME),
    ]:
        assert anon.request(method, path).status_code == 401, (method, path)


def test_logout_removes_cookie_from_browser():
    c = logged_in(STUDENT)
    res = c.post("/api/v1/auth/logout")
    set_cookie = res.headers["set-cookie"]
    assert set_cookie.startswith(f"{settings.AUTH_COOKIE_NAME}=")
    assert "Max-Age=0" in set_cookie
    assert "HttpOnly" in set_cookie and "Secure" in set_cookie
    assert c.get(ME).status_code == 401


# --- Konfiguracja produkcyjna --------------------------------------------------------

@pytest.mark.parametrize("overrides", [
    {"APP_ENV": "production"},                                                   # domyślny klucz
    {"APP_ENV": "production", "SECRET_KEY": "za-krotki-klucz"},
    {"APP_ENV": "production", "SECRET_KEY": "s" * 64, "AUTH_COOKIE_SECURE": False},
    {"AUTH_COOKIE_SAMESITE": "none", "AUTH_COOKIE_SECURE": False},
    {"ALGORITHM": "none"},
    {"ALGORITHM": "RS256"},
])
def test_insecure_configuration_refused(overrides):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)


def test_secure_production_configuration_accepted():
    cfg = Settings(_env_file=None, APP_ENV="production", SECRET_KEY="k" * 64)
    assert cfg.AUTH_COOKIE_SECURE is True
    assert cfg.AUTH_COOKIE_SAMESITE == "strict"
