"""Recuperación de contraseña con código de un solo uso.

El código se crea de dos formas: la persona lo pide por correo
(`POST /auth/forgot-password`, si hay SMTP configurado) o el administrador
lo genera con `python -m app.cli create-reset-code --email ...` y se lo
entrega por un canal privado. Solo se guarda su hash.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from app.db import Connection, get_connection
from app.logging_config import logger
from app.mailer import MailError, send_email


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


RESET_EMAIL_BODY = """Hola {name}:

Alguien (esperamos que tú) ha pedido recuperar la contraseña de tu cuenta
de Fitness Tracker.

Tu código de recuperación es:

    {code}

Introdúcelo en la pantalla de inicio de sesión, en «He olvidado mi
contraseña», junto con tu correo y la contraseña nueva. Es de un solo uso
y caduca en {minutes} minutos.

Si no lo has pedido tú, ignora este mensaje: tu contraseña no cambiará.
"""


def send_reset_email(email: str) -> None:
    """Crea un código para `email` y se lo envía, si la cuenta existe y está
    activa. No devuelve nada ni falla hacia fuera: se ejecuta tras responder
    para que la respuesta no revele si la cuenta existe."""
    try:
        with get_connection() as connection:
            user = connection.execute(
                "SELECT id, display_name, is_active FROM users WHERE email = ?",
                (email,),
            ).fetchone()

            if user is None or not bool(user["is_active"]):
                return

            code, _ = create_password_reset(connection, user["id"])

        send_email(
            email,
            "Código para recuperar tu contraseña",
            RESET_EMAIL_BODY.format(
                name=user["display_name"],
                code=code,
                minutes=DEFAULT_RESET_MINUTES,
            ),
        )
        logger.info("Código de recuperación enviado: id=%s", user["id"])
    except MailError as error:
        logger.error("Recuperación por correo: %s", error)
    except Exception:
        logger.exception("Recuperación por correo: error inesperado")

