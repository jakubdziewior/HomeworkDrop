from typing import Iterator

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings

# Jednolite nazwy ograniczeń – czytelne komunikaty błędów i stabilne migracje.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _create_engine(url: str) -> Engine:
    kwargs: dict = {"pool_pre_ping": True, "echo": settings.DB_ECHO}

    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            # Baza w pamięci (testy) – jedno współdzielone połączenie.
            kwargs["poolclass"] = StaticPool

    new_engine = create_engine(url, **kwargs)

    if new_engine.dialect.name == "sqlite":
        @event.listens_for(new_engine, "connect")
        def _enable_sqlite_foreign_keys(dbapi_connection, _record):
            # SQLite domyślnie NIE egzekwuje kluczy obcych.
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return new_engine


engine = _create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Tworzy brakujące tabele (istniejące pozostają bez zmian)."""
    import app.models  # noqa: F401 – rejestracja modeli w metadanych

    Base.metadata.create_all(bind=engine)
