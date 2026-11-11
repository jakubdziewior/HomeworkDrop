import os

# Ustawiane przed importem aplikacji – testy zawsze działają na bazie w pamięci,
# niezależnie od zawartości pliku .env.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import pytest  # noqa: E402

import app.models  # noqa: E402,F401
from app.database import Base, SessionLocal, engine  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    """Osobna sesja do sprawdzania/modyfikowania stanu bazy w testach."""
    with SessionLocal() as session:
        yield session
