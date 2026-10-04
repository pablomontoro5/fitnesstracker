"""Recuperación de contraseña sin correo.

El administrador genera un código de un solo uso con
`python -m app.cli create-reset-code --email ...` y se lo entrega a la
persona por un canal privado. Solo se guarda su hash.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.db import Connection


DEFAULT_RESET_MINUTES = 60


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_reset_code(code: str) -> str:
    # Códigos aleatorios de alta entropía: basta un hash rápido.
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def create_password_reset(
    connection: Connection,
    user_id: int,
    minutes: int = DEFAULT_RESET_MINUTES,
    now: datetime | None = None,
) -> tuple[str, str]:
    """Crea un código y anula los anteriores sin usar de ese usuario."""
    created_at = now or datetime.now(timezone.utc)
    expires_at = created_at + timedelta(minutes=minutes)
    code = secrets.token_urlsafe(16)

    connection.execute(
        """
        UPDATE password_resets
        SET used_at = ?
        WHERE user_id = ? AND used_at IS NULL
        """,
        (created_at.isoformat(timespec="seconds"), user_id),
    )
    connection.execute(
        """
        INSERT INTO password_resets (
            user_id,
            code_hash,
            created_at,
            expires_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            hash_reset_code(code),
            created_at.isoformat(timespec="seconds"),
            expires_at.isoformat(timespec="seconds"),
        ),
    )

    return code, expires_at.isoformat(timespec="seconds")


def invalid_reset() -> HTTPException:
    # Mismo error si el email no existe, el código es otro o ha caducado.
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="El email o el código de recuperación no son válidos.",
    )


def find_valid_reset_id(
    connection: Connection,
    user_id: int,
    code: str,
) -> int:
    row = connection.execute(
        """
        SELECT id
        FROM password_resets
        WHERE user_id = ?
          AND code_hash = ?
          AND used_at IS NULL
          AND expires_at > ?
        """,
        (user_id, hash_reset_code(code), _now()),
    ).fetchone()

    if row is None:
        raise invalid_reset()

    return row["id"]


def consume_password_reset(
    connection: Connection,
    reset_id: int,
) -> None:
    cursor = connection.execute(
        """
        UPDATE password_resets
        SET used_at = ?
        WHERE id = ? AND used_at IS NULL
        """,
        (_now(), reset_id),
    )

    # Si otra petición lo gastó entre medias, se deshace el cambio.
    if cursor.rowcount != 1:
        raise invalid_reset()
