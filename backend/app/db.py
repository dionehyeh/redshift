from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from app.config import settings


class DatabaseConnection:
    def __init__(self, connection: psycopg2.extensions.connection):
        self._connection = connection

    def execute(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> RealDictCursor:
        cursor = self._connection.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query.replace("?", "%s"), params)
        return cursor

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def get_connection() -> DatabaseConnection:
    database_url = settings.database_url.strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL must be set to a Neon PostgreSQL connection string"
        )
    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url.removeprefix("postgres://")
    if not database_url.startswith("postgresql://"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL; SQLite is no longer supported")

    return DatabaseConnection(psycopg2.connect(database_url, sslmode="require"))


@contextmanager
def get_db() -> Generator[DatabaseConnection, None, None]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _execute_script(conn: DatabaseConnection, sql: str) -> None:
    for statement in sql.split(";"):
        if statement.strip():
            conn.execute(statement)


def init_db(schema_path: str | None = None) -> None:
    path = (
        Path(schema_path)
        if schema_path
        else Path(__file__).resolve().parents[1] / "data/schema.sql"
    )
    if not path.exists():
        raise FileNotFoundError(f"Database schema not found: {path}")

    with get_db() as conn:
        _execute_script(conn, path.read_text(encoding="utf-8"))
        migration_path = (
            Path(__file__).resolve().parents[1] / "migrations/002_clerk_auth.sql"
        )
        if migration_path.exists():
            _execute_script(conn, migration_path.read_text(encoding="utf-8"))
        migration_path = (
            Path(__file__).resolve().parents[1] / "migrations/003_plan_card_robustness.sql"
        )
        if migration_path.exists():
            _execute_script(conn, migration_path.read_text(encoding="utf-8"))
