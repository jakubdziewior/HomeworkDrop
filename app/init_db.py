"""
Inicjalizacja schematu bazy danych.

Użycie:
    python -m app.init_db            # tworzy brakujące tabele
    python -m app.init_db --seed     # + konta testowe (tylko APP_ENV=development)
    python -m app.init_db --sql      # wypisuje DDL (CREATE TABLE ...) bez zmian w bazie
"""

import argparse

from sqlalchemy.schema import CreateIndex, CreateTable

from app.config import settings
from app.database import Base, SessionLocal, engine, init_db
from app.services.auth_service import seed_demo_users


def print_ddl() -> None:
    import app.models  # noqa: F401

    for table in Base.metadata.sorted_tables:
        print(f"{str(CreateTable(table).compile(engine)).strip()};")
        for index in sorted(table.indexes, key=lambda i: i.name):
            print(f"{CreateIndex(index).compile(engine)};")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inicjalizacja schematu bazy HomeworkDrop")
    parser.add_argument("--seed", action="store_true", help="dodaj konta testowe (tylko development)")
    parser.add_argument("--sql", action="store_true", help="wypisz DDL schematu i zakończ")
    args = parser.parse_args()

    if args.sql:
        print_ddl()
        return

    init_db()
    print(f"Schemat bazy zainicjalizowany ({engine.url.render_as_string(hide_password=True)}).")

    if args.seed:
        if settings.APP_ENV != "development":
            raise SystemExit("Konta testowe można tworzyć tylko przy APP_ENV=development.")
        with SessionLocal() as db:
            seed_demo_users(db)
        print("Dodano konta testowe.")


if __name__ == "__main__":
    main()
