import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.security import hash_password, validate_password_strength, verify_password

client = TestClient(app, base_url="https://testserver")


@pytest.fixture(autouse=True)
def clean_users():
    client.cookies.clear()
    yield
    client.cookies.clear()


@pytest.mark.unit
def test_hash_password_returns_bcrypt_hash():
    plain = "SuperTajneHaslo123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert hashed.startswith("$2b$")


@pytest.mark.unit
def test_verify_password_accepts_correct_password():
    plain = "SuperTajneHaslo123!"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


@pytest.mark.unit
def test_verify_password_rejects_wrong_password():
    hashed = hash_password("SuperTajneHaslo123!")
    assert verify_password("ZleHaslo123!", hashed) is False


@pytest.mark.unit
def test_verify_password_handles_corrupted_hash():
    assert verify_password("SuperTajneHaslo123!", "nieprawidlowy-hash") is False


@pytest.mark.unit
def test_validate_password_accepts_strong_password():
    validate_password_strength("SilneHaslo123!")


@pytest.mark.unit
def test_validate_password_rejects_too_short():
    with pytest.raises(HTTPException) as exc_info:
        validate_password_strength("Krot1!")
    assert exc_info.value.status_code == 400
    assert "co najmniej 8 znaków" in exc_info.value.detail


@pytest.mark.unit
def test_validate_password_rejects_missing_digit():
    with pytest.raises(HTTPException) as exc_info:
        validate_password_strength("BezCyfryZnak!")
    assert exc_info.value.status_code == 400
    assert "co najmniej jedną cyfrę" in exc_info.value.detail


@pytest.mark.unit
def test_validate_password_rejects_missing_uppercase():
    with pytest.raises(HTTPException) as exc_info:
        validate_password_strength("bez_wielkiej_123!")
    assert exc_info.value.status_code == 400
    assert "co najmniej jedną wielką literę" in exc_info.value.detail


@pytest.mark.unit
def test_validate_password_rejects_missing_special_character():
    with pytest.raises(HTTPException) as exc_info:
        validate_password_strength("BezZnakuSpecjalnego123")
    assert exc_info.value.status_code == 400
    assert "co najmniej jeden znak specjalny" in exc_info.value.detail


@pytest.mark.unit
def test_registration_success():
    payload = {
        "email": "p.zielinski@student.edu.pl",
        "password": "HasloStudenta123!",
        "full_name": "Piotr Zieliński",
        "role": "student",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "p.zielinski@student.edu.pl"
    assert data["full_name"] == "Piotr Zieliński"
    assert data["role"] == "student"
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.unit
def test_registration_normalizes_email_to_lowercase():
    payload = {
        "email": "P.Zielinski@Student.Edu.PL",
        "password": "HasloStudenta123!",
        "full_name": "Piotr Zieliński",
        "role": "student",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["email"] == "p.zielinski@student.edu.pl"


@pytest.mark.unit
def test_registration_duplicate_email():
    payload = {
        "email": "p.zielinski@student.edu.pl",
        "password": "HasloStudenta123!",
        "full_name": "Piotr Zieliński",
        "role": "student",
    }
    first = client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 400
    assert "już istnieje" in second.json()["detail"]


@pytest.mark.unit
def test_registration_rejects_invalid_email():
    payload = {
        "email": "niepoprawny-email",
        "password": "HasloStudenta123!",
        "full_name": "Piotr Zieliński",
        "role": "student",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.unit
def test_registration_rejects_invalid_role():
    payload = {
        "email": "p.zielinski@student.edu.pl",
        "password": "HasloStudenta123!",
        "full_name": "Piotr Zieliński",
        "role": "admin",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.unit
def test_login_success():
    reg_payload = {
        "email": "t.kaminski@uczelnia.edu.pl",
        "password": "HasloProwadzacego123!",
        "full_name": "dr Tomasz Kamiński",
        "role": "teacher",
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    login_payload = {
        "email": "t.kaminski@uczelnia.edu.pl",
        "password": "HasloProwadzacego123!",
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    data = login_res.json()
    assert data["message"] == "Logowanie zakończone sukcesem."
    assert data["user"]["email"] == "t.kaminski@uczelnia.edu.pl"
    assert data["user"]["role"] == "teacher"


@pytest.mark.unit
def test_login_invalid_password():
    reg_payload = {
        "email": "p.zielinski@student.edu.pl",
        "password": "HasloStudenta123!",
        "full_name": "Piotr Zieliński",
        "role": "student",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "p.zielinski@student.edu.pl",
        "password": "ZleHaslo123!",
    }
    res = client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 401
    assert "Nieprawidłowy adres email lub hasło." in res.json()["detail"]


@pytest.mark.unit
def test_login_nonexistent_user():
    login_payload = {
        "email": "nieznany@homeworkdrop.pl",
        "password": "HasloStudenta123!",
    }
    res = client.post("/api/v1/auth/login", json=login_payload)
    assert res.status_code == 401
    assert "Nieprawidłowy adres email lub hasło." in res.json()["detail"]
