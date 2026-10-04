#!/usr/bin/env bash
# Descarga la última copia, la descifra y comprueba que es un volcado válido de
# PostgreSQL con las tablas de la aplicación.
# Úsalo de vez en cuando (y tras configurar las copias): una copia que no se ha
# probado a restaurar no es una copia. Para una prueba completa, restaura el
# volcado en una base vacía (ver docs/DEPLOY.md).
#
# Uso: deploy/verify-backup.sh <ruta a la clave privada age>
# Se ejecuta en TU ordenador (donde está la clave privada), no en el servidor.
# Variable necesaria: RCLONE_REMOTE (p. ej. b2:mi-bucket/fitness)
# Opcional: PG_IMAGE (por defecto postgres:17-alpine).
set -euo pipefail

IDENTITY="${1:?Uso: $0 <clave-privada-age>}"
: "${RCLONE_REMOTE:?Define RCLONE_REMOTE}"
PG_IMAGE="${PG_IMAGE:-postgres:17-alpine}"

latest="$(rclone lsf "$RCLONE_REMOTE" --include 'fitness_tracker_*.dump.age' | sort | tail -n 1)"
[[ -n "$latest" ]] || { echo "No hay copias en $RCLONE_REMOTE" >&2; exit 1; }

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

rclone copyto "$RCLONE_REMOTE/$latest" "$workdir/$latest"
age -d -i "$IDENTITY" -o "$workdir/restored.dump" "$workdir/$latest"

# pg_restore --list lee el índice del volcado: falla si el archivo está dañado.
toc="$(docker run --rm -v "$workdir:/backup:ro" "$PG_IMAGE" \
    pg_restore --list /backup/restored.dump)"

for table in users daily_logs workout_sessions nutrition_meals; do
    grep -Eq "TABLE DATA public ${table} " <<<"$toc" \
        || { echo "Falta la tabla $table en la copia" >&2; exit 1; }
done

echo "Última copia verificada: $latest"
