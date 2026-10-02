"""Utilidades de administración. Se ejecutan en el servidor:

    python -m app.cli create-invite [--days 7]
    python -m app.cli backup [--output-dir DIR | --stdout]
"""
import argparse
import sqlite3
import sys
import tempfile
from pathlib import Path

from app.db import DATABASE_PATH, get_connection, initialize_database
from app.invitations import DEFAULT_INVITATION_DAYS, create_invitation
from app.services.backups import create_database_backup


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

    backup = subcommands.add_parser(
        "backup",
        help="Crea una copia SQLite portable y verificada.",
    )
    destination = backup.add_mutually_exclusive_group()
    destination.add_argument(
        "--output-dir",
        type=Path,
        help="Carpeta donde guardar la copia (por defecto data/backups).",
    )
    destination.add_argument(
        "--stdout",
        action="store_true",
        help=(
            "Escribe la copia en la salida estándar y no deja ningún "
            "archivo en disco. Pensado para cifrarla y subirla con una tubería."
        ),
    )

    return parser


def create_invite(days: int) -> int:
    initialize_database()

    with get_connection() as connection:
        code, expires_at = create_invitation(connection, days=days)

    print(f"Código de invitación: {code}")
    print(f"Caduca (UTC): {expires_at}")
    print("Un solo uso. Compártelo por un canal privado.")

    return 0


def verify_backup(path: Path) -> None:
    """Falla si la copia no es una base SQLite íntegra."""
    connection = sqlite3.connect(path)

    try:
        result = connection.execute("PRAGMA integrity_check").fetchone()
        has_users = connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' AND name = 'users'"
        ).fetchone()
    finally:
        connection.close()

    if result is None or result[0] != "ok" or has_users is None:
        raise RuntimeError("La copia generada no supera la verificación.")


def run_backup(output_dir: Path | None, to_stdout: bool) -> int:
    if not DATABASE_PATH.exists():
        print(
            f"No existe la base de datos en {DATABASE_PATH}.",
            file=sys.stderr,
        )
        return 1

    if to_stdout:
        # Con --stdout la copia nunca se queda en disco: se genera en una
        # carpeta temporal, se verifica y se vuelca a la salida estándar.
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = create_database_backup(Path(temporary_directory))
            verify_backup(path)
            sys.stdout.buffer.write(path.read_bytes())
            sys.stdout.buffer.flush()

        return 0

    path = create_database_backup(output_dir)
    verify_backup(path)
    print(path)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "create-invite":
        if args.days <= 0:
            parser.error("--days debe ser un entero positivo.")

        return create_invite(args.days)

    if args.command == "backup":
        return run_backup(args.output_dir, args.stdout)

    parser.error("Comando desconocido.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
