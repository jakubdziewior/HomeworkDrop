import os
from pathlib import Path

# Ustawiane przed importem aplikacji – testy zawsze działają na bazie w pamięci,
# niezależnie od zawartości pliku .env.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_ENV"] = "test"

import bcrypt  # noqa: E402
import pytest  # noqa: E402

import app.models  # noqa: E402,F401
from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402

_TESTS_DIR = Path(__file__).parent
_CATEGORY_DIRS = ("unit", "integration", "security")


def pytest_collection_modifyitems(config, items):
    """Automatyczne oznaczanie testów markerem odpowiadającym katalogowi (np. -m security)."""
    for item in items:
        try:
            rel = Path(item.fspath).relative_to(_TESTS_DIR)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] in _CATEGORY_DIRS:
            item.add_marker(getattr(pytest.mark, rel.parts[0]))


@pytest.fixture(scope="session", autouse=True)
def fast_password_hashing():
    """
    bcrypt z 12 rundami trwa ~0,3 s na hash – w testach (setki rejestracji/logowań)
    używamy minimalnego kosztu 4. Algorytm i format hasha pozostają te same.
    """
    original = bcrypt.gensalt
    bcrypt.gensalt = lambda rounds=4, prefix=b"2b": original(rounds=rounds, prefix=prefix)
    yield
    bcrypt.gensalt = original


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def upload_dir(tmp_path, monkeypatch):
    """Każdy test zapisuje pliki w osobnym katalogu tymczasowym, nigdy w ./uploads."""
    path = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(path))
    return path


@pytest.fixture
def db():
    """Osobna sesja do sprawdzania/modyfikowania stanu bazy w testach."""
    with SessionLocal() as session:
        yield session
