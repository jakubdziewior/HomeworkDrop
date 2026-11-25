import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import app
from app.security import hash_password, validate_password_strength, verify_password

# HTTPS, aby klient testowy odsyłał ciasteczka z flagą Secure.
client = TestClient(app, base_url="https://testserver")


@pytest.fixture(autouse=True)
def clean_users():
    client.cookies.clear()
    yield


def test_password_hashing_and_verification():
    plain = "SuperTajneHaslo123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("ZleHaslo123!", hashed) is False


def test_password_strength_accepts_strong_password():
    assert validate_password_strength("MocneHaslo123!") is None


@pytest.mark.parametrize("password,expected_message", [
    ("Krot1!", "co najmniej 8 znaków"),
    ("BezCyfryZnakuWielkiej!", "co najmniej jedną cyfrę"),
    ("bez_wielkiej_litery_123!", "co najmniej jedną wielką literę"),
    ("BezZnakuSpecjalnego123", "co najmniej jeden znak specjalny"),
], ids=["too-short", "no-digit", "no-uppercase", "no-special-char"])
def test_password_strength_rejects_weak_password(password, expected_message):
    with pytest.raises(HTTPException) as exc_info:
        validate_password_strength(password)
    assert exc_info.value.status_code == 400
    assert expected_message in exc_info.value.detail


def test_registration_success():
    payload = {
        "email": "p.zielinski@student.edu.pl",
        "password": "HasloStudenta123!",
        "full_name": "Piotr Zieliński",
        "role": "student"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "p.zielinski@student.edu.pl"
    assert data["full_name"] == "Piotr Zieliński"
    assert data["role"] == "student"
    assert "password" not in data
    assert "hashed_password" not in data


def test_registration_duplicate_email():
    payload = {
        "email": "p.zielinski@student.edu.pl",
        "password": "HasloStudenta123!",
        "full_name": "Piotr Zieliński",
        "role": "student"
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 400
    assert "już istnieje" in second.json()["detail"]


def test_login_success():
    reg_payload = {
        "email": "t.kaminski@uczelnia.edu.pl",
        "password": "HasloProwadzacego123!",
        "full_name": "dr Tomasz Kamiński",
        "role": "teacher"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    login_payload = {
        "email": "t.kaminski@uczelnia.edu.pl",
        "password": "HasloProwadzacego123!"
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["message"] == "Logowanie zakończone sukcesem."
    assert data["user"]["email"] == "t.kaminski@uczelnia.edu.pl"
    assert data["user"]["role"] == "teacher"


def test_login_invalid_password():
    reg_payload = {
        "email": "p.zielinski@student.edu.pl",
        "password": "HasloStudenta123!",
        "full_name": "Piotr Zieliński",
        "role": "student"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "p.zielinski@student.edu.pl",
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
