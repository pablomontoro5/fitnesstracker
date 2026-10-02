"""Utilidades de administración. Se ejecutan en el servidor:

    python -m app.cli create-invite [--days 7]
"""
import argparse

from app.db import get_connection, initialize_database
from app.invitations import DEFAULT_INVITATION_DAYS, create_invitation


def main(argv: list[str] | None = None) -> int:
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

    args = parser.parse_args(argv)

    if args.days <= 0:
        parser.error("--days debe ser un entero positivo.")

    initialize_database()

    with get_connection() as connection:
        code, expires_at = create_invitation(connection, days=args.days)

    print(f"Código de invitación: {code}")
    print(f"Caduca (UTC): {expires_at}")
    print("Un solo uso. Compártelo por un canal privado.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
