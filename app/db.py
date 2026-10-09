"""Acceso a PostgreSQL (Supabase).

El resto de la aplicación usa una interfaz muy parecida a la de `sqlite3`
(`connection.execute(sql, params)`, filas accesibles por nombre, `?` como
marcador, `cursor.lastrowid`), de modo que las consultas no tienen que
reescribirse: esta capa las traduce a PostgreSQL.

Configuración:
- FITNESS_TRACKER_DATABASE_URL: cadena de conexión (obligatoria).
- FITNESS_TRACKER_DB_POOL_MAX: máximo de conexiones del pool (10 por defecto).
"""
import os
import re
import threading
from functools import lru_cache
from pathlib import Path

import psycopg
from psycopg.errors import IntegrityError  # noqa: F401  (se reexporta)
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.schema import ROW_LEVEL_SECURITY_STATEMENTS, SCHEMA_STATEMENTS


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_URL_ENV = "FITNESS_TRACKER_DATABASE_URL"
POOL_MAX_ENV = "FITNESS_TRACKER_DB_POOL_MAX"

# Mismo formato que tenía CURRENT_TIMESTAMP en SQLite: "AAAA-MM-DD HH:MM:SS" UTC.
UTC_NOW_SQL = "to_char(now() AT TIME ZONE 'utc', 'YYYY-MM-DD HH24:MI:SS')"

_SCHEMA_LOCK_KEY = 727_274


class DatabaseConfigError(RuntimeError):
    pass


def get_database_url() -> str:
    url = os.environ.get(DATABASE_URL_ENV, "").strip()

    if not url:
        raise DatabaseConfigError(
            f"Falta {DATABASE_URL_ENV}: la cadena de conexión de PostgreSQL "
            "(en Supabase: Project Settings → Database → Connection string)."
        )

    return url


# ---------------------------------------------------------------------------
# Traducción de SQL estilo SQLite a PostgreSQL
# ---------------------------------------------------------------------------

_INSERT_RE = re.compile(r"^\s*INSERT\s+INTO\s+(\w+)", re.IGNORECASE)
# Tablas sin columna id: no se les puede pedir RETURNING id.
_TABLES_WITHOUT_ID = {"schema_migrations"}
_RETURNING_RE = re.compile(r"\bRETURNING\b", re.IGNORECASE)
_CURRENT_TIMESTAMP_RE = re.compile(r"\bCURRENT_TIMESTAMP\b", re.IGNORECASE)


@lru_cache(maxsize=2048)
def translate_sql(sql: str) -> str:
    """`?` → `%s`, `%` literal → `%%` y CURRENT_TIMESTAMP con el formato de texto.

    Los literales entre comillas simples se respetan tal cual (salvo `%`, que
    psycopg también interpretaría).
    """
    sql = _CURRENT_TIMESTAMP_RE.sub(f"({UTC_NOW_SQL})", sql)

    result: list[str] = []
    in_string = False

    for character in sql:
        if character == "'":
            in_string = not in_string
            result.append(character)
        elif character == "%":
            result.append("%%")
        elif character == "?" and not in_string:
            result.append("%s")
        else:
            result.append(character)

    return "".join(result)


def _with_returning_id(sql: str) -> str:
    match = _INSERT_RE.match(sql)

    if (
        match
        and match.group(1).lower() not in _TABLES_WITHOUT_ID
        and not _RETURNING_RE.search(sql)
    ):
        return sql.rstrip().rstrip(";") + " RETURNING id"

    return sql


class Cursor:
    """Resultado de `execute`: filas por nombre, `rowcount` y `lastrowid`."""

    def __init__(self, cursor, lastrowid=None) -> None:
        self._cursor = cursor
        self.lastrowid = lastrowid

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def __iter__(self):
        return iter(self._cursor)


class Connection:
    """Conexión con transacción: `with get_connection() as c:` confirma al
    salir (o revierte si hubo una excepción) y devuelve la conexión al pool."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool
        self._raw = pool.getconn()

    def execute(self, sql: str, params=()) -> Cursor:
        translated = translate_sql(sql)
        returning = _with_returning_id(translated)
        cursor = self._raw.execute(returning, params)

        if returning != translated and cursor.description is not None:
            row = cursor.fetchone()
            return Cursor(cursor, lastrowid=row["id"] if row else None)

        return Cursor(cursor)

    def executemany(self, sql: str, params_seq) -> None:
        with self._raw.cursor() as cursor:
            cursor.executemany(translate_sql(sql), params_seq)

    def commit(self) -> None:
        self._raw.commit()

    def rollback(self) -> None:
        self._raw.rollback()

    def close(self) -> None:
        if self._raw is None:
            return

        try:
            # Si quedó una transacción a medias, no se devuelve sucia al pool.
            self._raw.rollback()
        finally:
            self._pool.putconn(self._raw)
            self._raw = None

    def __enter__(self) -> "Connection":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            if exc_type is None:
                self._raw.commit()
            else:
                self._raw.rollback()
        finally:
            self.close()


# ---------------------------------------------------------------------------
# Pool
# ---------------------------------------------------------------------------

_pool: ConnectionPool | None = None
_pool_url: str | None = None
_pool_lock = threading.Lock()


def _get_pool() -> ConnectionPool:
    global _pool, _pool_url

    url = get_database_url()

    with _pool_lock:
        if _pool is not None and _pool_url != url:
            _pool.close()
            _pool = None

        if _pool is None:
            # Una conexión de prueba muestra el error real (contraseña, red,
            # IPv6...) en vez de un PoolTimeout genérico tras 15 segundos.
            try:
                psycopg.connect(url, connect_timeout=10).close()
            except psycopg.OperationalError as error:
                raise DatabaseConfigError(
                    f"No se pudo conectar con la base de datos: {error}"
                ) from error

            _pool = ConnectionPool(
                url,
                min_size=1,
                max_size=int(os.environ.get(POOL_MAX_ENV, "10")),
                kwargs={
                    "row_factory": dict_row,
                    # El pooler de Supabase en modo transacción no admite
                    # sentencias preparadas en el servidor.
                    "prepare_threshold": None,
                },
                # Descarta conexiones cortadas por el servidor o el pooler.
                check=ConnectionPool.check_connection,
                max_idle=300,
                open=True,
                timeout=15,
            )
            _pool_url = url

        return _pool


def close_pool() -> None:
    global _pool, _pool_url

    with _pool_lock:
        if _pool is not None:
            _pool.close()

        _pool = None
        _pool_url = None


def get_connection() -> Connection:
    """Devuelve una conexión del pool (úsala con `with`)."""
    return Connection(_get_pool())


# ---------------------------------------------------------------------------
# Esquema y migraciones
# ---------------------------------------------------------------------------

# (versión, descripción, sentencias). Para cambiar el esquema en el futuro,
# añade una entrada nueva: nunca edites una ya aplicada.
MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (1, "esquema inicial", SCHEMA_STATEMENTS + ROW_LEVEL_SECURITY_STATEMENTS),
]


def initialize_database() -> None:
    """Aplica las migraciones pendientes (idempotente y seguro con varios
    procesos arrancando a la vez)."""
    with get_connection() as connection:
        # El bloqueo se libera al terminar la transacción.
        connection.execute(
            "SELECT pg_advisory_xact_lock(%s)" % _SCHEMA_LOCK_KEY
        )
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT ({UTC_NOW_SQL})
            )
            """
        )

        applied = {
            row["version"]
            for row in connection.execute(
                "SELECT version FROM schema_migrations"
            ).fetchall()
        }

        for version, description, statements in MIGRATIONS:
            if version in applied:
                continue

            for statement in statements:
                connection.execute(statement)

            connection.execute(
                "INSERT INTO schema_migrations (version, description) "
                "VALUES (?, ?)",
                (version, description),
            )


def is_unique_violation(error: BaseException) -> bool:
    """Indica si el error es una violación de restricción UNIQUE."""
    return isinstance(error, psycopg.errors.UniqueViolation)
