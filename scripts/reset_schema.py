"""Drop and recreate the benchmarking schema (required after UUID PK migration)."""

from __future__ import annotations

from dotenv import load_dotenv
from sqlalchemy import text

from backend.app.config import settings
from backend.app.db.session import engine, init_schema
from backend.app.models.entities import Base


def main() -> None:
    load_dotenv()
    schema = settings.db_schema
    init_schema()

    with engine.begin() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))

    Base.metadata.create_all(bind=engine)
    print(f'Recreated schema "{schema}" with UUID primary keys.')


if __name__ == "__main__":
    main()
