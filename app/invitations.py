"""Registro por invitación.

Los códigos se generan en el servidor con `python -m app.cli create-invite`
y solo se guarda su hash, de modo que una copia de la base de datos no
revela códigos válidos.
"""
import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status


REGISTRATION_MODE_ENV = "FITNESS_TRACKER_REGISTRATION_MODE"
REGISTRATION_MODES = ("invite", "open")
DEFAULT_INVITATION_DAYS = 7


def get_registration_mode() -> str:
    mode = os.environ.get(REGISTRATION_MODE_ENV, "invite").strip().lower()

    if mode not in REGISTRATION_MODES:
        raise RuntimeError(
            f"{REGISTRATION_MODE_ENV} debe ser 'invite' u 'open'."
        )

    return mode


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_invitation_code(code: str) -> str:
    # Los códigos son aleatorios de alta entropía: basta un hash rápido.
    return hashlib.sha256(code.strip().encode("utf-8")).hexdigest()


def create_invitation(
    connection: sqlite3.Connection,
    days: int = DEFAULT_INVITATION_DAYS,
    now: datetime | None = None,
) -> tuple[str, str]:
    """Crea una invitación y devuelve (código en claro, caducidad)."""
    created_at = now or datetime.now(timezone.utc)
    expires_at = created_at + timedelta(days=days)
    code = secrets.token_urlsafe(16)

    connection.execute(
        """
        INSERT INTO invitations (code_hash, created_at, expires_at)
        VALUES (?, ?, ?)
        """,
        (
            hash_invitation_code(code),
            created_at.isoformat(timespec="seconds"),
            expires_at.isoformat(timespec="seconds"),
        ),
    )

    return code, expires_at.isoformat(timespec="seconds")


def invalid_invitation() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Se necesita un código de invitación válido.",
    )


def find_valid_invitation_id(
    connection: sqlite3.Connection,
    code: str | None,
) -> int:
    """Devuelve el id de la invitación o lanza 403 (mismo error siempre)."""
    if not code or not code.strip():
        raise invalid_invitation()

    row = connection.execute(
        """
        SELECT id
        FROM invitations
        WHERE code_hash = ?
          AND used_at IS NULL
          AND expires_at > ?
        """,
        (hash_invitation_code(code), _now()),
    ).fetchone()

    if row is None:
        raise invalid_invitation()

    return row["id"]


def consume_invitation(
    connection: sqlite3.Connection,
    invitation_id: int,
    user_id: int,
) -> None:
    cursor = connection.execute(
        """
        UPDATE invitations
        SET used_at = ?, used_by_user_id = ?
        WHERE id = ? AND used_at IS NULL
        """,
        (_now(), user_id, invitation_id),
    )

    # Si otra petición la gastó entre medias, se deshace todo el registro.
    if cursor.rowcount != 1:
        raise invalid_invitation()
