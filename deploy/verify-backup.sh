#!/usr/bin/env bash
# Descarga la última copia, la descifra y comprueba su integridad.
# Úsalo de vez en cuando (y tras configurar las copias): una copia que no se ha
# probado a restaurar no es una copia.
#
# Uso: deploy/verify-backup.sh <ruta a la clave privada age>
# Se ejecuta en TU ordenador (donde está la clave privada), no en el servidor.
# Variable necesaria: RCLONE_REMOTE (p. ej. b2:mi-bucket/fitness)
set -euo pipefail

IDENTITY="${1:?Uso: $0 <clave-privada-age>}"
: "${RCLONE_REMOTE:?Define RCLONE_REMOTE}"

latest="$(rclone lsf "$RCLONE_REMOTE" --include 'fitness_tracker_*.db.age' | sort | tail -n 1)"
[[ -n "$latest" ]] || { echo "No hay copias en $RCLONE_REMOTE" >&2; exit 1; }

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

rclone copyto "$RCLONE_REMOTE/$latest" "$workdir/$latest"
age -d -i "$IDENTITY" -o "$workdir/restored.db" "$workdir/$latest"

python3 - "$workdir/restored.db" <<'PY'
import sqlite3
import sys

connection = sqlite3.connect(sys.argv[1])
assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
print(f"Copia correcta. Cuentas de usuario: {users}")
PY

echo "Última copia verificada: $latest"
