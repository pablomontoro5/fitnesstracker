#!/usr/bin/env bash
# Copia nocturna: vuelca la base de datos de Supabase con pg_dump, la cifra con
# age y la sube al almacenamiento remoto con rclone.
# La copia viaja por una tubería: nunca se guarda sin cifrar en el servidor.
#
# Configuración en el archivo indicado por BACKUP_ENV (por defecto
# /etc/fitness-tracker/backup.env). Ver docs/DEPLOY.md.
set -euo pipefail

ENV_FILE="${BACKUP_ENV:-/etc/fitness-tracker/backup.env}"
# shellcheck disable=SC1090
source "$ENV_FILE"

: "${BACKUP_DATABASE_URL:?Falta BACKUP_DATABASE_URL (conexión de Supabase) en $ENV_FILE}"
: "${AGE_RECIPIENT:?Falta AGE_RECIPIENT (clave pública age) en $ENV_FILE}"
: "${RCLONE_REMOTE:?Falta RCLONE_REMOTE (p. ej. b2:mi-bucket/fitness) en $ENV_FILE}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
# La versión de pg_dump debe ser igual o superior a la de Supabase.
PG_IMAGE="${PG_IMAGE:-postgres:17-alpine}"

name="fitness_tracker_$(date -u +%Y-%m-%dT%H-%M-%SZ).dump.age"

# Se sube con extensión .partial y solo se renombra si toda la tubería ha ido
# bien; así una copia truncada nunca parece una copia válida.
# La URL se pasa por entorno para que no aparezca en la lista de procesos.
docker run --rm -e PGCONNECT_URL="$BACKUP_DATABASE_URL" "$PG_IMAGE" \
    sh -c 'pg_dump --dbname="$PGCONNECT_URL" --format=custom --schema=public --no-owner --no-privileges' \
  | age -r "$AGE_RECIPIENT" \
  | rclone rcat "$RCLONE_REMOTE/$name.partial"

rclone moveto "$RCLONE_REMOTE/$name.partial" "$RCLONE_REMOTE/$name"

# La limpieza va después de la subida: si la copia falla, el script termina
# antes y no se borra nada.
rclone delete "$RCLONE_REMOTE" \
    --min-age "${RETENTION_DAYS}d" \
    --include "fitness_tracker_*.dump.age"
rclone delete "$RCLONE_REMOTE" --min-age 2d --include "*.partial"

# Aviso opcional de «latido» (por ejemplo healthchecks.io): si dejas de recibirlo,
# el servicio te avisa de que las copias han dejado de hacerse.
if [[ -n "${HEALTHCHECK_URL:-}" ]]; then
    curl -fsS --retry 3 -o /dev/null "$HEALTHCHECK_URL" || true
fi

echo "Copia subida: $RCLONE_REMOTE/$name"
