import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.security import hash_password, validate_password_strength, verify_password
from app.services.auth_service import reset_users_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_users():
    reset_users_db()
    yield
    reset_users_db()


def test_password_hashing_and_verification():
    plain = "SuperTajneHaslo123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("ZleHaslo123!", hashed) is False


def test_password_strength_validation():
    with pytest.raises(Exception) as exc_info:
        validate_password_strength("Krot1!")
    assert "co najmniej 8 znaków" in str(exc_info.value.detail)

    with pytest.raises(Exception) as exc_info:
        validate_password_strength("BezCyfryZnakuWielkiej")
    assert "co najmniej jedną cyfrę" in str(exc_info.value.detail)

    with pytest.raises(Exception) as exc_info:
        validate_password_strength("bez_wielkiej_litery_123!")
    assert "co najmniej jedną wielką literę" in str(exc_info.value.detail)

    with pytest.raises(Exception) as exc_info:
        validate_password_strength("BezZnakuSpecjalnego123")
    assert "co najmniej jeden znak specjalny" in str(exc_info.value.detail)


def test_registration_success():
    payload = {
        "email": "student@homeworkdrop.pl",
        "password": "HasloStudenta123!",
        "full_name": "Jan Kowalski",
        "role": "student"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "student@homeworkdrop.pl"
    assert data["full_name"] == "Jan Kowalski"
    assert data["role"] == "student"
    assert "password" not in data
    assert "hashed_password" not in data


def test_registration_duplicate_email():
    payload = {
        "email": "student@homeworkdrop.pl",
        "password": "HasloStudenta123!",
        "full_name": "Jan Kowalski",
        "role": "student"
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 400
    assert "już istnieje" in second.json()["detail"]


def test_login_success():
    reg_payload = {
        "email": "teacher@homeworkdrop.pl",
        "password": "HasloProwadzacego123!",
        "full_name": "Dr inż. Adam Nowak",
        "role": "teacher"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    login_payload = {
        "email": "teacher@homeworkdrop.pl",
        "password": "HasloProwadzacego123!"
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["message"] == "Logowanie zakończone sukcesem."
    assert data["user"]["email"] == "teacher@homeworkdrop.pl"
    assert data["user"]["role"] == "teacher"


def test_login_invalid_password():
    reg_payload = {
        "email": "student@homeworkdrop.pl",
        "password": "HasloStudenta123!",
        "full_name": "Jan Kowalski",
        "role": "student"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "student@homeworkdrop.pl",
        "password": "ZleHaslo123!"
    }
    res = client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 401
    assert "Nieprawidłowy adres email lub hasło." in res.json()["detail"]


def test_login_nonexistent_user():
    login_payload = {
        "email": "nieznany@homeworkdrop.pl",
        "password": "HasloStudenta123!"
    }
    res = client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 401
    assert "Nieprawidłowy adres email lub hasło." in res.json()["detail"]
