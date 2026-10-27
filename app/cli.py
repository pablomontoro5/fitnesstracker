"""Utilidades de administración. Se ejecutan en el servidor:

    python -m app.cli create-invite [--days 7]
    python -m app.cli create-reset-code --email EMAIL [--minutes 60]
    python -m app.cli test-email --to EMAIL
"""
import argparse
import sys
from app.db import get_connection, initialize_database
from app.invitations import DEFAULT_INVITATION_DAYS, create_invitation
from app.mailer import MailError, mail_is_configured, send_email
from app.password_resets import DEFAULT_RESET_MINUTES, create_password_reset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subcommands = parser.add_subparsers(dest="command", required=True)

    invite = subcommands.add_parser(
        "create-invite",
        help="Genera un código de invitación de un solo uso.",
    )
    invite.add_argument(
        "--days",
        type=int,
        default=DEFAULT_INVITATION_DAYS,
        help=f"Días de validez (por defecto {DEFAULT_INVITATION_DAYS}).",
    )

    reset = subcommands.add_parser(
        "create-reset-code",
        help="Genera un código de recuperación de contraseña de un solo uso.",
    )
    reset.add_argument("--email", required=True, help="Email de la cuenta.")
    reset.add_argument(
        "--minutes",
        type=int,
        default=DEFAULT_RESET_MINUTES,
        help=f"Minutos de validez (por defecto {DEFAULT_RESET_MINUTES}).",
    )

    test_email = subcommands.add_parser(
        "test-email",
        help="Envía un correo de prueba para comprobar la configuración SMTP.",
    )
    test_email.add_argument("--to", required=True, help="Destinatario.")

    return parser


def create_invite(days: int) -> int:
    initialize_database()

    with get_connection() as connection:
        code, expires_at = create_invitation(connection, days=days)

    print(f"Código de invitación: {code}")
    print(f"Caduca (UTC): {expires_at}")
    print("Un solo uso. Compártelo por un canal privado.")

    return 0


def create_reset_code(email: str, minutes: int) -> int:
    initialize_database()

    with get_connection() as connection:
        user = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email.strip().lower(),),
        ).fetchone()

        if user is None:
            print(f"No existe ninguna cuenta con el email {email}.", file=sys.stderr)
            return 1

        code, expires_at = create_password_reset(
            connection,
            user["id"],
            minutes=minutes,
        )

    print(f"Código de recuperación: {code}")
    print(f"Caduca (UTC): {expires_at}")
    print("Un solo uso. Entrégalo a su dueño por un canal privado.")
    print("Anula cualquier código anterior sin usar de esa cuenta.")

    return 0


def test_email(to: str) -> int:
    if not mail_is_configured():
        print(
            "Falta configurar FITNESS_TRACKER_SMTP_HOST y "
            "FITNESS_TRACKER_MAIL_FROM.",
            file=sys.stderr,
        )
        return 1

    try:
        send_email(
            to.strip(),
            "Prueba de Fitness Tracker",
            "Si lees esto, el envío de correo funciona.",
        )
    except MailError as error:
        print(str(error), file=sys.stderr)
        return 1

    print(f"Correo de prueba enviado a {to}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "create-invite":
        if args.days <= 0:
            parser.error("--days debe ser un entero positivo.")

        return create_invite(args.days)

    if args.command == "create-reset-code":
        if args.minutes <= 0:
            parser.error("--minutes debe ser un entero positivo.")

        return create_reset_code(args.email, args.minutes)

    if args.command == "test-email":
        return test_email(args.to)

    parser.error("Comando desconocido.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
