"""Envío de correo por SMTP (opcional).

Solo se usa para la recuperación de contraseña. Sin configuración, la
función queda desactivada y la recuperación sigue siendo manual
(`python -m app.cli create-reset-code`).

Funciona con cualquier proveedor que ofrezca SMTP (Resend, Brevo, Mailgun,
Amazon SES, el SMTP de tu dominio...). No hay dependencias nuevas: solo
la biblioteca estándar.

Variables de entorno:
    FITNESS_TRACKER_SMTP_HOST      servidor (si falta, el correo está apagado)
    FITNESS_TRACKER_SMTP_PORT      587 (STARTTLS, por defecto) o 465 (TLS)
    FITNESS_TRACKER_SMTP_USER      usuario (opcional)
    FITNESS_TRACKER_SMTP_PASSWORD  contraseña o clave de API (opcional)
    FITNESS_TRACKER_MAIL_FROM      remitente, p. ej. "Fitness Tracker <no-reply@tu-dominio.com>"
"""
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import parseaddr

SMTP_HOST_ENV = "FITNESS_TRACKER_SMTP_HOST"
SMTP_PORT_ENV = "FITNESS_TRACKER_SMTP_PORT"
SMTP_USER_ENV = "FITNESS_TRACKER_SMTP_USER"
SMTP_PASSWORD_ENV = "FITNESS_TRACKER_SMTP_PASSWORD"
MAIL_FROM_ENV = "FITNESS_TRACKER_MAIL_FROM"

DEFAULT_SMTP_PORT = 587
SMTP_TIMEOUT_SECONDS = 15


class MailError(Exception):
    """El correo no se pudo enviar. El mensaje no incluye credenciales."""


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def mail_is_configured() -> bool:
    return bool(_env(SMTP_HOST_ENV)) and bool(parseaddr(_env(MAIL_FROM_ENV))[1])


def _smtp_port() -> int:
    raw = _env(SMTP_PORT_ENV)

    if not raw:
        return DEFAULT_SMTP_PORT

    try:
        port = int(raw)
    except ValueError:
        raise MailError(f"{SMTP_PORT_ENV} no es un número válido.") from None

    if not 1 <= port <= 65535:
        raise MailError(f"{SMTP_PORT_ENV} está fuera de rango.")

    return port


def send_email(to: str, subject: str, body: str) -> None:
    """Envía un correo de texto plano. Lanza MailError si falla."""
    if not mail_is_configured():
        raise MailError("El envío de correo no está configurado.")

    if "\n" in to or "\r" in to or "\n" in subject or "\r" in subject:
        # Evita inyección de cabeceras.
        raise MailError("Destinatario o asunto no válidos.")

    message = EmailMessage()
    message["From"] = _env(MAIL_FROM_ENV)
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    host = _env(SMTP_HOST_ENV)
    port = _smtp_port()
    user = _env(SMTP_USER_ENV)
    password = os.environ.get(SMTP_PASSWORD_ENV, "")
    context = ssl.create_default_context()

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(
                host, port, timeout=SMTP_TIMEOUT_SECONDS, context=context
            )
        else:
            server = smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT_SECONDS)

        with server:
            if port != 465:
                server.starttls(context=context)

            if user:
                server.login(user, password)

            server.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        # Solo el tipo de error: el texto puede traer datos del servidor.
        raise MailError(
            f"No se pudo enviar el correo ({type(error).__name__})."
        ) from None
